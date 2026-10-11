"""What a thread hangs on, and finding it again after the code has moved.

Every kind of anchor answers three questions that need what the review
holds: what does it say, what is around it, and where is it now. A handler
per kind answers them, and the rest of the review asks this service instead
of looking inside an anchor.
"""

from abc import ABC, abstractmethod
from typing import Self, assert_never, override

from pydantic import BaseModel

from claude_review.domain.exceptions import AnchorLinesNotShownError, AnchorTooLongError, UnknownAnchorFileError
from claude_review.domain.models import MAX_QUOTE_LINES, Anchor, AnchorBase, DiffFile, LineAnchor, LineSide, LineType
from claude_review.services.place_words import line_span, place_in_words

# How many of the review's files a refusal names, so whoever named the wrong
# one can see what the right one is called without the whole list
FILES_NAMED_IN_REFUSAL = 5
# How many lines either side of its own an excerpt of lines quotes, so a
# comment on one sentence is read with the ones it follows from
EXCERPT_REACH = 2


class SideLine(BaseModel):
    """One line of one side of a file, with the number it has there."""

    number: int
    content: str


class AnchorHandler[Kind: AnchorBase](ABC):
    """What answers for one kind of anchor, against what the review holds."""

    @abstractmethod
    def quote(self, anchor: Kind) -> Kind:
        """The anchor with what it is about read off what the review holds."""

    @abstractmethod
    def check_quote(self, anchor: Kind) -> None:
        """Refuse an anchor whose quote does not hold what it names, piece for piece.

        A page quotes what the reader picked as they picked it, and the agent
        takes the quote for what a suggestion replaces: named but not quoted,
        a part would be replaced by whoever never saw it.
        """

    @abstractmethod
    def excerpt(self, anchor: Kind) -> list[str]:
        """What the anchor is on, with what stands around it, as the review holds it; nothing if it holds none."""

    @abstractmethod
    def follow(self, anchor: Kind) -> Kind:
        """The anchor moved onto what the review holds now, or marked outdated."""


class LineAnchorHandler(AnchorHandler[LineAnchor]):
    """Line anchors, read against the review's own diff."""

    def __init__(self, diff_files: list[DiffFile]) -> None:
        self._files = {file.path: file for file in diff_files}
        # Each side of each file, read off the diff once however many anchors ask
        self._side_lines: dict[LineSide, dict[str, list[SideLine]]] = {side: {} for side in LineSide}

    @override
    def quote(self, anchor: LineAnchor) -> LineAnchor:
        """The anchor with the lines it names read off the diff.

        Raises:
            AnchorTooLongError: if it names more lines than a thread may quote:
                such a thread could never be sent in a round.
            UnknownAnchorFileError: if the file is not in this review.
            AnchorLinesNotShownError: if the diff does not show those lines of it.
        """
        line_count = anchor.end_line - anchor.start_line + 1
        if line_count > MAX_QUOTE_LINES:
            msg = f"a thread may hang on at most {MAX_QUOTE_LINES} lines, not {line_count}"
            raise AnchorTooLongError(msg)

        shown = self._files.get(anchor.file)
        if shown is None:
            listed = ", ".join(list(self._files)[:FILES_NAMED_IN_REFUSAL])
            msg = f"{anchor.file} is not in this review. It has: {listed}"
            raise UnknownAnchorFileError(msg)

        on_screen = {line.number: line.content for line in self._lines_of(shown, anchor.side)}
        wanted = range(anchor.start_line, anchor.end_line + 1)
        missing = [number for number in wanted if number not in on_screen]
        if missing:
            side = "removed" if anchor.side == LineSide.OLD else "new"
            plural = "s" if len(missing) > 1 else ""
            msg = f"{anchor.file} does not show {side} line{plural} {line_span(missing[0], missing[-1])}"
            raise AnchorLinesNotShownError(msg)

        return _changed(anchor, quote=[on_screen[number] for number in wanted], outdated=False)

    @override
    def check_quote(self, anchor: LineAnchor) -> None:
        """Refuse lines quoted short of the span they name: one quoted line for each, or none kept at all.

        A thread kept from before quotes were kept quotes nothing, and has
        nothing to fall short of.

        Raises:
            AnchorLinesNotShownError: if the quote holds fewer or more lines than the anchor names.
        """
        line_count = anchor.end_line - anchor.start_line + 1
        if anchor.quote and len(anchor.quote) != line_count:
            msg = (
                f"{place_in_words(anchor)} names {line_count} lines but quotes {len(anchor.quote)}:"
                " a comment covers only lines on screen"
            )
            raise AnchorLinesNotShownError(msg)

    @override
    def excerpt(self, anchor: LineAnchor) -> list[str]:
        """The anchor's lines and `EXCERPT_REACH` more either side, from the side of the file it is on.

        A file the review does not hold has nothing to show: a thread may
        outlive the content it was written on.
        """
        shown = self._files.get(anchor.file)
        if shown is None:
            return []
        around = range(anchor.start_line - EXCERPT_REACH, anchor.end_line + EXCERPT_REACH + 1)
        return [line.content for line in self._lines_of(shown, anchor.side) if line.number in around]

    @override
    def follow(self, anchor: LineAnchor) -> LineAnchor:
        """Where the anchor's lines are in the diff as it now stands.

        The lines it quotes are looked for and the anchor follows them; when
        they are gone it stays on its old numbers and says so, rather than
        pointing at whatever has slid into their place. One that never kept
        its lines has nothing to search for, and is left where it is.
        """
        if not anchor.quote:
            return _changed(anchor, outdated=False)

        shown = self._files.get(anchor.file)
        if shown is None:
            return _changed(anchor, outdated=True)

        lines = self._lines_of(shown, anchor.side)
        found = _find_run(lines, anchor.quote, near=anchor.start_line)
        if found is None:
            return _changed(anchor, outdated=True)

        return _changed(
            anchor,
            start_line=lines[found].number,
            end_line=lines[found + len(anchor.quote) - 1].number,
            outdated=False,
        )

    def _lines_of(self, file: DiffFile, side: LineSide) -> list[SideLine]:
        known = self._side_lines[side]
        if file.path not in known:
            known[file.path] = _side_lines(file, side)
        return known[file.path]


class AnchorService:
    """Every kind of anchor, each answered by the handler that knows it.

    Built once for each take of what the review holds: the handlers read it
    once, however many anchors ask.
    """

    def __init__(self, lines: AnchorHandler[LineAnchor]) -> None:
        self._lines = lines

    @classmethod
    def of_diff(cls, diff_files: list[DiffFile]) -> Self:
        """The anchors of one take of the review's diff."""
        return cls(lines=LineAnchorHandler(diff_files))

    def quote(self, anchor: Anchor) -> Anchor:
        """The anchor with what it is about read off what the review holds.

        Raises:
            UnknownAnchorFileError: if the review holds no such file.
            AnchorLinesNotShownError: if the diff does not show those lines.
        """
        match anchor:
            case LineAnchor():
                return self._lines.quote(anchor)
            case _:
                assert_never(anchor)

    def check_quote(self, anchor: Anchor) -> None:
        """Refuse an anchor the reader's page made whose quote does not hold what it names.

        Raises:
            AnchorLinesNotShownError: if it names lines it does not quote.
        """
        match anchor:
            case LineAnchor():
                self._lines.check_quote(anchor)
            case _:
                assert_never(anchor)

    def excerpt(self, anchor: Anchor) -> list[str]:
        """What the anchor is on, with what stands around it, as the review holds it; nothing if it holds none."""
        match anchor:
            case LineAnchor():
                return self._lines.excerpt(anchor)
            case _:
                assert_never(anchor)

    def follow(self, anchor: Anchor) -> Anchor:
        """The anchor moved onto what the review holds now, or marked outdated."""
        match anchor:
            case LineAnchor():
                return self._lines.follow(anchor)
            case _:
                assert_never(anchor)


def _side_lines(file: DiffFile, side: LineSide) -> list[SideLine]:
    """Every line of one side of a file, in order.

    A removed line exists only on the old side; everything else, context
    included, is read as the new file.
    """
    removed_side = side == LineSide.OLD
    return [
        SideLine(number=number, content=line.content)
        for hunk in file.hunks
        for line in hunk.lines
        if (line.kind == LineType.DELETE) == removed_side
        and (number := line.old_number if removed_side else line.new_number) is not None
    ]


def _changed(anchor: LineAnchor, **changes: object) -> LineAnchor:
    """The anchor with some fields changed, checked again as any anchor is.

    `model_copy` would skip the checks, and an anchor built here goes out to
    the browser and comes back in a round, where they are applied.
    """
    return LineAnchor.model_validate({**anchor.model_dump(), **changes})


def _find_run(lines: list[SideLine], quote: list[str], *, near: int) -> int | None:
    """Where the quoted lines stand together, nearest to where they were.

    A short quote — a closing brace, `return None` — stands in many places,
    and the one nearest the old numbers is the one that moved least; of two
    as near, the earlier, so the choice is the same every time.
    """
    starts = [start for start in range(len(lines) - len(quote) + 1) if _stands_at(lines, quote, start)]
    return min(starts, key=lambda start: abs(lines[start].number - near), default=None)


def _stands_at(lines: list[SideLine], quote: list[str], start: int) -> bool:
    """Whether the quote is the file's own run of lines from `start`.

    Neighbours in the list are not always neighbours in the file: the last
    line of one hunk is followed by the first of the next, however far apart
    the two stand.
    """
    first = lines[start].number
    return all(
        lines[start + offset].content == text and lines[start + offset].number == first + offset
        for offset, text in enumerate(quote)
    )

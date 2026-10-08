"""What a thread hangs on, and finding it again after the code has moved.

Every kind of anchor answers three questions: what does it say, where is it
now, and how is its place named. A handler per kind answers them, and the
rest of the review asks this service instead of looking inside an anchor.
"""

from typing import assert_never

from pydantic import BaseModel

from claude_review.domain.exceptions import AnchorLinesNotShownError, UnknownAnchorFileError
from claude_review.domain.models import Anchor, DiffFile, LineAnchor, LineSide, LineType

# How many of the review's files a refusal names, so whoever named the wrong
# one can see what the right one is called without the whole list
FILES_NAMED_IN_REFUSAL = 5


class SideLine(BaseModel):
    """One line of one side of a file, with the number it has there."""

    number: int
    content: str


class LineAnchorHandler:
    """Line anchors, read against the review's own diff."""

    def __init__(self, diff_files: list[DiffFile]) -> None:
        self._files = {file.path: file for file in diff_files}
        # Each side of each file, read off the diff once however many anchors ask
        self._side_lines: dict[LineSide, dict[str, list[SideLine]]] = {side: {} for side in LineSide}

    def quote(self, anchor: LineAnchor) -> LineAnchor:
        """The anchor with the lines it names read off the diff.

        Raises:
            UnknownAnchorFileError: if the file is not in this review.
            AnchorLinesNotShownError: if the diff does not show those lines of it.
        """
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
            msg = f"{anchor.file} does not show {side} line{plural} {_span(missing[0], missing[-1])}"
            raise AnchorLinesNotShownError(msg)

        return anchor.model_copy(update={"quote": [on_screen[number] for number in wanted], "outdated": False})

    def follow(self, anchor: LineAnchor) -> LineAnchor:
        """Where the anchor's lines are in the diff as it now stands.

        The lines it quotes are looked for and the anchor follows them; when
        they are gone it stays on its old numbers and says so, rather than
        pointing at whatever has slid into their place. One that never kept
        its lines has nothing to search for, and is left where it is.
        """
        if not anchor.quote:
            return anchor.model_copy(update={"outdated": False})

        shown = self._files.get(anchor.file)
        if shown is None:
            return anchor.model_copy(update={"outdated": True})

        lines = self._lines_of(shown, anchor.side)
        found = _find_run(lines, anchor.quote, near=anchor.start_line)
        if found is None:
            return anchor.model_copy(update={"outdated": True})

        return anchor.model_copy(
            update={
                "start_line": lines[found].number,
                "end_line": lines[found + len(anchor.quote) - 1].number,
                "outdated": False,
            }
        )

    def where(self, anchor: LineAnchor) -> str:
        """The place as the review writes it: "`a.py`:42-47", or "… (removed)".

        A removed line exists only in the file as it was, so its number is
        said to belong there, or it would be read against the current file.
        """
        removed = " (removed)" if anchor.side == LineSide.OLD else ""
        return f"`{anchor.file}`:{_span(anchor.start_line, anchor.end_line)}{removed}"

    def _lines_of(self, file: DiffFile, side: LineSide) -> list[SideLine]:
        known = self._side_lines[side]
        if file.path not in known:
            known[file.path] = _side_lines(file, side)
        return known[file.path]


class AnchorService:
    """Every kind of anchor, each answered by the handler that knows it."""

    def __init__(self, diff_files: list[DiffFile]) -> None:
        self._lines = LineAnchorHandler(diff_files)

    def quote(self, anchor: Anchor) -> Anchor:
        """The anchor with what it is about read off what the review holds.

        Raises:
            AnchorRefusedError: if nothing the review holds is where it points.
        """
        match anchor:
            case LineAnchor():
                return self._lines.quote(anchor)
            case _:
                assert_never(anchor)

    def follow(self, anchor: Anchor) -> Anchor:
        """The anchor moved onto what the review holds now, or marked outdated."""
        match anchor:
            case LineAnchor():
                return self._lines.follow(anchor)
            case _:
                assert_never(anchor)

    def where(self, anchor: Anchor) -> str:
        """The anchor's place, named the same way wherever it is told."""
        match anchor:
            case LineAnchor():
                return self._lines.where(anchor)
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
        if (line.type == LineType.DELETE) == removed_side
        and (number := line.old_no if removed_side else line.new_no) is not None
    ]


def _find_run(lines: list[SideLine], quote: list[str], *, near: int) -> int | None:
    """Where the quoted lines stand together, nearest to where they were.

    A short quote — a closing brace, `return None` — stands in many places,
    and the one nearest the old numbers is the one that moved least.
    """
    starts = [
        start
        for start in range(len(lines) - len(quote) + 1)
        if all(lines[start + offset].content == text for offset, text in enumerate(quote))
    ]
    return min(starts, key=lambda start: abs(lines[start].number - near), default=None)


def _span(start: int, end: int) -> str:
    """A range the way a person says it: "12", or "12-19"."""
    return str(start) if start == end else f"{start}-{end}"

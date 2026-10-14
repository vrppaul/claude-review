"""What a thread hangs on, and finding it again after the code has moved.

Every kind of anchor answers three questions that need what the review
holds: what does it say, what is around it, and where is it now. A handler
per kind answers them, and the rest of the review asks this service instead
of looking inside an anchor.
"""

from abc import ABC, abstractmethod
from typing import assert_never, override

from pydantic import BaseModel

from claude_review.domain.exceptions import (
    AnchorLinesNotShownError,
    AnchorTooLongError,
    UnknownAnchorFileError,
    UnknownStoryBlockError,
)
from claude_review.domain.models import (
    FIRST_ITEM,
    MAX_QUOTE_LINES,
    Anchor,
    AnchorBase,
    ChapterBlock,
    ChapterText,
    DiffFile,
    ItemBlock,
    LineAnchor,
    LineSide,
    LineType,
    OverviewBlock,
    OverviewList,
    OverviewText,
    ReasonBlock,
    StoryAnchor,
    StoryBlock,
)
from claude_review.domain.story import Chapter, StoryOverview, ToldStep, ToldStory
from claude_review.services.place_words import line_span, place_in_words

# How many of the review's files a refusal names, so whoever named the wrong
# one can see what the right one is called without the whole list
FILES_NAMED_IN_REFUSAL = 5
# How many lines either side of its own an excerpt of lines quotes, so a
# comment on one sentence is read with the ones it follows from
EXCERPT_REACH = 2
# How a refusal names the files of the review, each side's lines, and one
# line or more
FILES_SEPARATOR = ", "
SIDE_WORDS = {LineSide.OLD: "removed", LineSide.NEW: "new"}
ONE_LINE = "line"
SEVERAL_LINES = "lines"
# How a refusal says a story holds no such block, or that no story is told
NOT_IN_THE_STORY = "The story told of this review says nothing at {place}"
NO_STORY_TOLD = "No story is told of this review: nothing is at {place}"


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
            listed = FILES_SEPARATOR.join(list(self._files)[:FILES_NAMED_IN_REFUSAL])
            msg = f"{anchor.file} is not in this review. It has: {listed}"
            raise UnknownAnchorFileError(msg)

        on_screen = {line.number: line.content for line in self._lines_of(shown, anchor.side)}
        wanted = range(anchor.start_line, anchor.end_line + 1)
        missing = [number for number in wanted if number not in on_screen]
        if missing:
            lines = ONE_LINE if len(missing) == 1 else SEVERAL_LINES
            span = line_span(missing[0], missing[-1])
            msg = f"{anchor.file} does not show {SIDE_WORDS[anchor.side]} {lines} {span}"
            raise AnchorLinesNotShownError(msg)

        return anchor.quoting([on_screen[number] for number in wanted])

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
            return anchor.current_at(anchor.start_line, anchor.end_line)

        shown = self._files.get(anchor.file)
        if shown is None:
            return anchor.lost()

        lines = self._lines_of(shown, anchor.side)
        found = _find_run(lines, anchor.quote, near=anchor.start_line)
        if found is None:
            return anchor.lost()

        return anchor.current_at(lines[found].number, lines[found + len(anchor.quote) - 1].number)

    def _lines_of(self, file: DiffFile, side: LineSide) -> list[SideLine]:
        known = self._side_lines[side]
        if file.path not in known:
            known[file.path] = _side_lines(file, side)
        return known[file.path]


class StoryAnchorHandler(AnchorHandler[StoryAnchor]):
    """Anchors on blocks of the story's words, read against the story the review holds.

    What a block said when the thread was written is what the thread is
    about. The story is replaced whole when it is told again, and the thread
    follows its words: to its own block while that says them still, to the
    first block that does when another does, and nowhere when none does — it
    then stays where it was, outdated.
    """

    def __init__(self, story: ToldStory | None) -> None:
        # Every block the story held says something at, with its words, in the order the story tells them:
        # None while no story is told
        self._said = None if story is None else _said_in(story)

    @override
    def quote(self, anchor: StoryAnchor) -> StoryAnchor:
        """The anchor with the words its block says read off the story.

        Raises:
            UnknownStoryBlockError: if no story is told, or the one told says nothing at the block.
        """
        if self._said is None:
            raise UnknownStoryBlockError(NO_STORY_TOLD.format(place=place_in_words(anchor)))
        words = self._said.get(anchor.block)
        if words is None:
            raise UnknownStoryBlockError(NOT_IN_THE_STORY.format(place=place_in_words(anchor)))
        return anchor.quoting(words)

    @override
    def check_quote(self, anchor: StoryAnchor) -> None:
        """Take whatever words the page quotes: no suggestion replaces a story's words, so none is held to them."""

    @override
    def excerpt(self, anchor: StoryAnchor) -> list[str]:
        """The words the anchor quotes, which are all there is of a block."""
        return anchor.quote

    @override
    def follow(self, anchor: StoryAnchor) -> StoryAnchor:
        """The anchor on the block that says what it quotes, its own first; outdated where it was when none does.

        A review started again holds no story until one is told, and an
        anchor that never kept its words has none to look for: either is
        left as it is.
        """
        if self._said is None or not anchor.quote:
            return anchor
        [words] = anchor.quote
        if self._said.get(anchor.block) == words:
            return anchor.current_at(anchor.block)
        found = next((block for block, said in self._said.items() if said == words), None)
        if found is None:
            return anchor.lost()
        return anchor.current_at(found)


class AnchorService:
    """Every kind of anchor, each answered by the handler that knows it.

    Built for what the review holds as it is asked: a take of its content,
    whose handler reads it once however many anchors ask, and the story told
    of it.
    """

    def __init__(self, lines: AnchorHandler[LineAnchor], story: AnchorHandler[StoryAnchor]) -> None:
        self._lines = lines
        self._story = story

    def quote(self, anchor: Anchor) -> Anchor:
        """The anchor with what it is about read off what the review holds.

        Raises:
            UnknownAnchorFileError: if the review holds no such file.
            AnchorLinesNotShownError: if the diff does not show those lines.
            UnknownStoryBlockError: if the story told says nothing at the block, or none is told.
        """
        match anchor:
            case LineAnchor():
                return self._lines.quote(anchor)
            case StoryAnchor():
                return self._story.quote(anchor)
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
            case StoryAnchor():
                self._story.check_quote(anchor)
            case _:
                assert_never(anchor)

    def excerpt(self, anchor: Anchor) -> list[str]:
        """What the anchor is on, with what stands around it, as the review holds it; nothing if it holds none."""
        match anchor:
            case LineAnchor():
                return self._lines.excerpt(anchor)
            case StoryAnchor():
                return self._story.excerpt(anchor)
            case _:
                assert_never(anchor)

    def follow(self, anchor: Anchor) -> Anchor:
        """The anchor moved onto what the review holds now, or marked outdated."""
        match anchor:
            case LineAnchor():
                return self._lines.follow(anchor)
            case StoryAnchor():
                return self._story.follow(anchor)
            case _:
                assert_never(anchor)


def _said_in(story: ToldStory) -> dict[StoryBlock, str]:
    """Every block a story says something at, with its words, in the order the story tells them.

    A text the story left out — a doubt, a step's reason — is no block of
    it. Nor is the reason of a step of a file no thread could name.
    """
    blocks: dict[StoryBlock, str | None] = {
        **_overview_said(story.overview),
        **{block: words for chapter in story.chapters for block, words in _chapter_said(chapter).items()},
    }
    return {block: words for block, words in blocks.items() if words is not None}


def _overview_said(overview: StoryOverview) -> dict[StoryBlock, str | None]:
    """The overview's three lines, then every item of its lists, by their blocks."""
    lists = {
        OverviewList.DECISIONS: overview.decisions,
        OverviewList.TURNED_DOWN: overview.turned_down,
        OverviewList.LATER: overview.later,
    }
    return {
        OverviewBlock(text=OverviewText.TASK): overview.task,
        OverviewBlock(text=OverviewText.DONE): overview.done,
        OverviewBlock(text=OverviewText.DOUBT): overview.doubt,
        **{
            ItemBlock(list=listed, item=place): item.text
            for listed, items in lists.items()
            for place, item in enumerate(items, start=FIRST_ITEM)
        },
    }


def _chapter_said(chapter: Chapter[ToldStep]) -> dict[StoryBlock, str | None]:
    """What a chapter says of itself, then each of its steps' reasons, by their blocks."""
    return {
        ChapterBlock(chapter=chapter.id, text=ChapterText.WHY): chapter.why,
        ChapterBlock(chapter=chapter.id, text=ChapterText.DOUBT): chapter.doubt,
        **{
            ReasonBlock(file=step.file, first_line=step.lines.first): step.reason
            for step in chapter.steps
            if step.piece.commentable
        },
    }


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

"""How the review says a place in words, and reads lines back from the words for them.

An anchor is the place itself; the words for it depend on who reads them.
The agent's events, the catch-up index and the logs are text, and take plain
words. A round and the exit report are Markdown, and set the path as code,
so a name with an underscore or an asterisk in it is not read as emphasis.

A run of lines is written one way, "42" or "42-47", wherever a person
writes one — an option of a command, a step of a story's document. It is
written and read back here, with the one pattern for it and the one way
of saying what is not one, so they cannot come to differ.
"""

import re
from collections.abc import Callable
from typing import assert_never

from claude_review.domain.models import (
    FIRST_ITEM,
    Anchor,
    ChapterBlock,
    ChapterText,
    ItemBlock,
    LineAnchor,
    LineSide,
    LineSpan,
    OverviewBlock,
    OverviewList,
    OverviewText,
    ReasonBlock,
    StoryAnchor,
    StoryBlock,
)
from claude_review.services.markdown_code import code_span

# Said after the numbers of lines that exist only in the file as it was, or
# they would be read against the file as it is
REMOVED = " (removed)"
# What joins the first line of a run to its last
RANGE_SEPARATOR = "-"
# The most digits a line's number is written with: no file has a line past it
MOST_DIGITS = 10
# A run of lines as a person writes one: a line's number, or a first and a
# last. Anchored at both ends, so its pattern says the same to a schema, which
# reads a pattern as found anywhere in a text
LINES_WRITTEN = re.compile(rf"^[0-9]{{1,{MOST_DIGITS}}}({RANGE_SEPARATOR}[0-9]{{1,{MOST_DIGITS}}})?$")
# How a run of lines is written, shown to whoever wrote something else
LINES_EXAMPLE = '"42" or "42-47"'
# What is wrong with a text that names no lines: the rule, never the text,
# which whoever wrote it has
NOT_LINES = f"is not a line or a range of lines, like {LINES_EXAMPLE}"

# How each kind of block of a story's words is said: one of the overview's
# lines, an item of one of its lists, what a chapter says of itself, a step's reason
OVERVIEW_LINE_PLACE = "story overview, {line}"
ITEM_PLACE = "story overview, {item} {number}"
CHAPTER_PLACE = "story chapter {chapter}, {text}"
REASON_PLACE = "story step at {file}:{line}, its reason"
# The overview's lines, as the story's page heads them
OVERVIEW_LINE_WORDS = {OverviewText.TASK: "Task", OverviewText.DONE: "Done", OverviewText.DOUBT: "Doubt"}
# One item of each of the overview's lists
ITEM_WORDS = {
    OverviewList.DECISIONS: "decision",
    OverviewList.TURNED_DOWN: "turned down",
    OverviewList.LATER: "left for later",
}
# What a chapter says of itself
CHAPTER_TEXT_WORDS = {ChapterText.WHY: "why", ChapterText.DOUBT: "where to doubt"}
# The number a person says the first item of a list by
FIRST_ITEM_SAID = 1


def place_in_words(anchor: Anchor) -> str:
    """The place as plain text: "src/a.py:42-47", "story chapter images-kept, why"."""
    match anchor:
        case LineAnchor():
            return _lines_place(anchor, anchor.file)
        case StoryAnchor():
            return _block_place(anchor.block, str)
        case _:
            assert_never(anchor)


def place_in_markdown(anchor: Anchor) -> str:
    """The place as Markdown, a path or a chapter's id set as code: "`src/a.py`:42-47"."""
    match anchor:
        case LineAnchor():
            return _lines_place(anchor, code_span(anchor.file))
        case StoryAnchor():
            return _block_place(anchor.block, code_span)
        case _:
            assert_never(anchor)


def line_span(start: int, end: int) -> str:
    """A run of lines the way a person says it: "12", or "12-19"."""
    return str(start) if start == end else f"{start}{RANGE_SEPARATOR}{end}"


def lines_named(written: str) -> LineSpan:
    """The lines a person wrote as "12" or "12-19": what `line_span` writes, read back.

    Raises:
        ValueError: if it is neither a line's number nor a first and a last.
    """
    if LINES_WRITTEN.fullmatch(written) is None:
        raise ValueError(NOT_LINES)
    first, _, last = written.partition(RANGE_SEPARATOR)
    return LineSpan(first=int(first), last=int(last or first))


def _lines_place(anchor: LineAnchor, file_named: str) -> str:
    """Lines of a file, the file named as given: "a.py:42-47", or "a.py:42 (removed)"."""
    removed = REMOVED if anchor.side == LineSide.OLD else ""
    return f"{file_named}:{line_span(anchor.start_line, anchor.end_line)}{removed}"


def _block_place(block: StoryBlock, named: Callable[[str], str]) -> str:
    """A block of the story's words, a chapter's id or a step's file named as `named` writes it."""
    match block:
        case OverviewBlock():
            return OVERVIEW_LINE_PLACE.format(line=OVERVIEW_LINE_WORDS[block.text])
        case ItemBlock():
            number = block.item - FIRST_ITEM + FIRST_ITEM_SAID
            return ITEM_PLACE.format(item=ITEM_WORDS[block.list], number=number)
        case ChapterBlock():
            return CHAPTER_PLACE.format(chapter=named(block.chapter), text=CHAPTER_TEXT_WORDS[block.text])
        case ReasonBlock():
            return REASON_PLACE.format(file=named(block.file), line=block.first_line)
        case _:
            assert_never(block)

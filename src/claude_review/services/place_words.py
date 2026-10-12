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
from typing import assert_never

from claude_review.domain.models import Anchor, LineAnchor, LineSide, LineSpan
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


def place_in_words(anchor: Anchor) -> str:
    """The place as plain text: "src/a.py:42-47"."""
    match anchor:
        case LineAnchor():
            return _lines_place(anchor, anchor.file)
        case _:
            assert_never(anchor)


def place_in_markdown(anchor: Anchor) -> str:
    """The place as Markdown, its path set as code: "`src/a.py`:42-47"."""
    match anchor:
        case LineAnchor():
            return _lines_place(anchor, code_span(anchor.file))
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

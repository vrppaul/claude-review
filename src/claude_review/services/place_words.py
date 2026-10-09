"""How the review names the place a thread hangs on: in plain words, or in Markdown.

An anchor is the place itself; the words for it depend on who reads them.
The agent's events, the catch-up index and the logs are text, and take plain
words. A round and the exit report are Markdown, and set the path as code,
so a name with an underscore or an asterisk in it is not read as emphasis.
"""

import re
from typing import assert_never

from claude_review.domain.models import Anchor, LineAnchor, LineSide

# Said after the numbers of lines that exist only in the file as it was, or
# they would be read against the file as it is
REMOVED = " (removed)"
BACKTICK = "`"
# Every run of backticks in a text
BACKTICK_RUNS = re.compile(f"{BACKTICK}+")
# What sets code from a fence it would otherwise run into
FENCE_PADDING = " "


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
    return str(start) if start == end else f"{start}-{end}"


def code_span(text: str) -> str:
    """The text as Markdown code, whatever backticks it holds.

    The fence is one backtick longer than any run inside, so none of them
    closes it; text that starts or ends with a backtick is padded, so the
    fence is not read as longer than it is.
    """
    longest_run = max((len(run) for run in BACKTICK_RUNS.findall(text)), default=0)
    fence = BACKTICK * (longest_run + 1)
    padding = FENCE_PADDING if text.startswith(BACKTICK) or text.endswith(BACKTICK) else ""
    return f"{fence}{padding}{text}{padding}{fence}"


def _lines_place(anchor: LineAnchor, file_named: str) -> str:
    """Lines of a file, the file named as given: "a.py:42-47", or "a.py:42 (removed)"."""
    removed = REMOVED if anchor.side == LineSide.OLD else ""
    return f"{file_named}:{line_span(anchor.start_line, anchor.end_line)}{removed}"

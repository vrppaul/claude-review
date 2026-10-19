"""Functional requirement tests for code set apart in Markdown: nothing inside it closes it.

A fence of backticks is closed by the first run of as many backticks: in a
line of its own for a block, anywhere for inline code (CommonMark). Text
that holds backticks is fenced longer than any run of them.
"""

import re

from hypothesis import given, strategies as strategy

from claude_review.services.markdown_code import code_block

# Characters that make or break a fence, and room around them
FENCE_CHARACTERS = "` a\t"
# Enough lines and length for runs of every length to meet the fence
MOST_LINES = 6
LONGEST_LINE = 12
# What closes a fenced block of this many backticks: a line of at least as
# many, indented by three spaces at most, with nothing after them but spaces
CLOSING_FENCE = r" {{0,3}}`{{{length},}} *"


def _read_back(block: str) -> list[str]:
    """The lines of a fenced block, read as CommonMark reads one: up to the first line that closes its fence."""
    opening, *rest = block.split("\n")
    closes = re.compile(CLOSING_FENCE.format(length=len(opening)))
    closing = next(index for index, line in enumerate(rest) if closes.fullmatch(line))
    return rest[:closing]


def test_lines_without_a_backtick_take_the_shortest_fence() -> None:
    assert code_block(["x = 1"]) == "```\nx = 1\n```"


@given(strategy.lists(strategy.text(alphabet=FENCE_CHARACTERS, max_size=LONGEST_LINE), min_size=1, max_size=MOST_LINES))
def test_whatever_the_lines_hold_they_are_read_back_as_written(lines: list[str]) -> None:
    assert _read_back(code_block(lines)) == lines

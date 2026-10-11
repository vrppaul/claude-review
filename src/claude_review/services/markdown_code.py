"""Code set apart in Markdown, so that nothing inside it can close it.

A fence of backticks is closed by the first run of as many backticks — on a
line of its own for a block of code, anywhere for code inside a sentence
(CommonMark) — so a fence is one backtick longer than the longest run in
what it sets apart. Paths in a round's headings and the lines a thread was
written against hold whatever the reader's files hold, backticks included.
"""

import re

BACKTICK = "`"
# Every run of backticks in a text
BACKTICK_RUNS = re.compile(f"{BACKTICK}+")
# The fewest backticks that open a block of code; code in a sentence takes one
SHORTEST_BLOCK_FENCE = 3
SHORTEST_INLINE_FENCE = 1
# What sets code in a sentence apart from a fence it would otherwise run into
FENCE_PADDING = " "
LINE_BREAK = "\n"


def code_span(text: str) -> str:
    """The text as code inside a sentence, whatever backticks it holds.

    Text that starts or ends with a backtick is padded, so the fence is not
    read as longer than it is.
    """
    fence = _fence_around(text, shortest=SHORTEST_INLINE_FENCE)
    padding = FENCE_PADDING if text.startswith(BACKTICK) or text.endswith(BACKTICK) else ""
    return f"{fence}{padding}{text}{padding}{fence}"


def code_block(lines: list[str]) -> str:
    """The lines as a fenced block of code, whatever backticks they hold."""
    text = LINE_BREAK.join(lines)
    fence = _fence_around(text, shortest=SHORTEST_BLOCK_FENCE)
    return f"{fence}{LINE_BREAK}{text}{LINE_BREAK}{fence}"


def _fence_around(text: str, *, shortest: int) -> str:
    """One backtick more than the longest run in the text, and never fewer than the shortest fence of its kind."""
    longest_run = max((len(run) for run in BACKTICK_RUNS.findall(text)), default=0)
    return BACKTICK * max(shortest, longest_run + 1)

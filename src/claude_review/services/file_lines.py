"""A file's bytes read into lines as git numbers them, so a line one part of the review names is the same line to all.

The diff numbers a file's lines so, and a file read whole, the lines widened
in beside a hunk and the places a name stands in are numbered the same way:
parted at line feeds alone, each line read as UTF-8 with a byte that is not
replaced, as the diff shows it.
"""

# What ends a line, and nothing else does: a lone carriage return is part of the line it is in
LINE_END = b"\n"
# What a file's bytes are read as, and what stands for a byte that is not
TEXT_ENCODING = "utf-8"
NOT_TEXT = "replace"
# How git tells a binary file from text: a NUL byte among the first it reads
BINARY_CHECK_BYTES = 8000
BINARY_MARK = b"\0"


def lines_of(content: bytes) -> list[bytes]:
    """A file's lines without their line ends; a final line feed ends the last line rather than starting another."""
    lines = content.split(LINE_END)
    if not lines[-1]:
        lines.pop()
    return lines


def line_text(line: bytes) -> str:
    """One line's bytes as text, its line end left off where it has one."""
    return line.removesuffix(LINE_END).decode(TEXT_ENCODING, errors=NOT_TEXT)


def is_text(content: bytes) -> bool:
    """Whether a file's bytes are text, as git decides it: no NUL among the first it reads."""
    return BINARY_MARK not in content[:BINARY_CHECK_BYTES]

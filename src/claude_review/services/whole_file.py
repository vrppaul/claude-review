"""Text read whole, as the review shows it: a file every line of which can be commented on.

Plain files and the turns of a conversation are not changes, but the review
shows everything as a diff, so the same reading, commenting and sending work
for them too. Such a file is one hunk of context lines, numbered once: there
is no version before it.
"""

from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, LineType

# A whole file has no hunk header to show, no old side to start, and is
# numbered from its first line
NO_HUNK_HEADER = ""
NO_OLD_START = 0
FIRST_LINE = 1


def whole_file(path: str, text: str) -> DiffFile:
    """The text as a file of the review, every line a context line on the new side."""
    lines = [
        DiffLine(kind=LineType.CONTEXT, old_number=None, new_number=number, content=content)
        for number, content in enumerate(_lines_of(text), start=FIRST_LINE)
    ]
    hunk = DiffHunk(header=NO_HUNK_HEADER, old_start=NO_OLD_START, new_start=FIRST_LINE, lines=lines)
    return DiffFile(path=path, status=FileStatus.ADDED, hunks=[hunk])


def _lines_of(text: str) -> list[str]:
    """The text's lines; a final newline ends the last line rather than starting an empty one."""
    lines = text.split("\n")
    return lines[:-1] if lines[-1] == "" else lines

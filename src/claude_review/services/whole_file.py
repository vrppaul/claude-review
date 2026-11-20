"""Text read whole, as the review shows it: a file every line of which can be commented on.

Plain files, the turns of a conversation and the files of a take the change
did not touch are not changes, but the review shows everything as a diff, so
the same reading, commenting and sending work for them too. Such a file is
one hunk of context lines, numbered once: no change sets an old side apart.
"""

from claude_review.domain.models import (
    FIRST_LINE,
    NO_HUNK_HEADER,
    DiffFile,
    DiffHunk,
    DiffLine,
    FileStatus,
    LineType,
)
from claude_review.services.file_lines import line_text, lines_of


def whole_file(path: str, content: bytes) -> DiffFile:
    """A file's bytes as a file of the review with no version before it."""
    return DiffFile(path=path, status=FileStatus.ADDED, hunks=[whole_hunk(content)])


def whole_hunk(content: bytes) -> DiffHunk:
    """A file's bytes as one hunk, every line a context line on the new side, numbered as git numbers it."""
    lines = [
        DiffLine(kind=LineType.CONTEXT, old_number=None, new_number=number, content=line_text(line))
        for number, line in enumerate(lines_of(content), start=FIRST_LINE)
    ]
    # A whole file has no hunk header to show; its old side has no lines, and
    # starts where they would, as any side with none does
    return DiffHunk(header=NO_HUNK_HEADER, old_start=FIRST_LINE, new_start=FIRST_LINE, lines=lines)

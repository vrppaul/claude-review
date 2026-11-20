"""Text read whole, as the review shows it: a file every line of which can be commented on.

Plain files and the turns of a conversation are not changes, but the review
shows everything as a diff, so the same reading, commenting and sending work
for them too. Such a file is one hunk of context lines, numbered once: there
is no version before it.
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
from claude_review.services.file_lines import TEXT_ENCODING, line_text, lines_of


def whole_file(path: str, text: str) -> DiffFile:
    """The text as a file of the review, every line a context line on the new side, numbered as a file's are."""
    lines = [
        DiffLine(kind=LineType.CONTEXT, old_number=None, new_number=number, content=line_text(line))
        for number, line in enumerate(lines_of(text.encode(TEXT_ENCODING)), start=FIRST_LINE)
    ]
    # A whole file has no hunk header to show; its old side has no lines, and
    # starts where they would, as any side with none does
    hunk = DiffHunk(header=NO_HUNK_HEADER, old_start=FIRST_LINE, new_start=FIRST_LINE, lines=lines)
    return DiffFile(path=path, status=FileStatus.ADDED, hunks=[hunk])

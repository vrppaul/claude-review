"""Domain models for claude-review."""

from enum import StrEnum

from pydantic import BaseModel


class LineType(StrEnum):
    """Type of a diff line."""

    CONTEXT = "context"
    ADD = "add"
    DELETE = "delete"


class FileStatus(StrEnum):
    """Status of a file in the diff."""

    MODIFIED = "modified"
    ADDED = "added"
    DELETED = "deleted"
    RENAMED = "renamed"


class DiffLine(BaseModel):
    """A single line in a diff hunk."""

    type: LineType
    old_no: int | None = None
    new_no: int | None = None
    content: str


class DiffHunk(BaseModel):
    """A contiguous block of changes in a file."""

    header: str
    old_start: int
    new_start: int
    lines: list[DiffLine]


class DiffFile(BaseModel):
    """A file that has been changed."""

    path: str
    status: FileStatus
    hunks: list[DiffHunk]


class Comment(BaseModel):
    """A review comment on a specific line or range."""

    file: str
    start_line: int
    end_line: int
    body: str


class ReviewResult(BaseModel):
    """Formatted review output."""

    markdown: str
    comment_count: int

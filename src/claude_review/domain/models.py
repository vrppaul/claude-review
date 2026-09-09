"""Domain models for claude-review."""

from enum import StrEnum, auto

from pydantic import BaseModel


class ReviewMode(StrEnum):
    """What kind of content is being reviewed.

    DIFF  — git changes (the default): two-column line numbers, add/delete styling.
    FILES — plain text files (plans, docs): single line numbers, no diff decoration.
    TRANSCRIPT — conversation messages: each message is a reviewable block.
    """

    DIFF = auto()
    FILES = auto()
    TRANSCRIPT = auto()


class LineType(StrEnum):
    """Type of a diff line."""

    CONTEXT = auto()
    ADD = auto()
    DELETE = auto()


class LineSide(StrEnum):
    """Which version of the file a line belongs to.

    OLD — the version before the change; such a line no longer exists in the
    working tree, so its number only makes sense against the original file.
    NEW — the version after the change. Files and transcript modes have no
    "before", so every line there is NEW.
    """

    OLD = auto()
    NEW = auto()


class FileStatus(StrEnum):
    """Status of a file in the diff."""

    MODIFIED = auto()
    ADDED = auto()
    DELETED = auto()
    RENAMED = auto()


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
    """A review comment on a line or range of one side of the diff.

    Line numbers are only meaningful together with the side: a hunk that
    replaces a line has both an old line 42 and a new line 42.
    """

    file: str
    side: LineSide
    start_line: int
    end_line: int
    body: str


class ReviewResult(BaseModel):
    """Formatted review output."""

    markdown: str
    comment_count: int

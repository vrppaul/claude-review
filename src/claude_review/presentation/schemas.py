"""Pydantic request/response schemas for the API."""

from pydantic import BaseModel, Field, model_validator

from claude_review.domain.models import (
    CommentSeverity,
    DiffFile,
    LineSide,
    ReviewMode,
    ThreadQuestion,
)


class DiffResponse(BaseModel):
    """Response for GET /api/diff."""

    files: list[DiffFile]
    mode: ReviewMode
    title: str


class CommentInput(BaseModel):
    """A single comment in the submit request."""

    file: str = Field(min_length=1)
    side: LineSide
    severity: CommentSeverity
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    body: str = Field(min_length=1, max_length=50_000)

    @model_validator(mode="after")
    def start_before_end(self) -> CommentInput:
        if self.start_line > self.end_line:
            msg = "start_line must be <= end_line"
            raise ValueError(msg)
        return self


class SubmitRequest(BaseModel):
    """Request body for POST /api/submit."""

    comments: list[CommentInput]
    body: str | None = Field(default=None, max_length=50_000)


class SubmitResponse(BaseModel):
    """Response for POST /api/submit."""

    markdown: str
    comment_count: int


class FileWindowResponse(BaseModel):
    """Response for GET /api/file-window."""

    start: int
    lines: list[str]
    total: int


class AskRequest(BaseModel):
    """Request body for POST /api/ask — the reader asking about a thread."""

    thread_id: str = Field(min_length=1, max_length=200)
    file: str = Field(min_length=1)
    side: LineSide
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    quote: list[str] = Field(default_factory=list, max_length=200)
    body: str = Field(min_length=1, max_length=50_000)


class ReplyRequest(BaseModel):
    """Request body for POST /api/reply — the answer coming back."""

    thread_id: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=50_000)


class EventResponse(BaseModel):
    """Response for GET /api/events, the long poll an answerer waits on."""

    type: str
    question: ThreadQuestion | None = None

"""Pydantic request/response schemas for the API."""

from pydantic import BaseModel, Field, model_validator

from claude_review.domain.models import DiffFile, ReviewMode


class DiffResponse(BaseModel):
    """Response for GET /api/diff."""

    files: list[DiffFile]
    mode: ReviewMode


class CommentInput(BaseModel):
    """A single comment in the submit request."""

    file: str = Field(min_length=1)
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

"""Pydantic request/response schemas for the API."""

from pydantic import BaseModel

from claude_review.domain.models import DiffFile


class DiffResponse(BaseModel):
    """Response for GET /api/diff."""

    files: list[DiffFile]


class CommentInput(BaseModel):
    """A single comment in the submit request."""

    file: str
    start_line: int
    end_line: int
    body: str


class SubmitRequest(BaseModel):
    """Request body for POST /api/submit."""

    comments: list[CommentInput]


class SubmitResponse(BaseModel):
    """Response for POST /api/submit."""

    markdown: str
    comment_count: int

"""Pydantic request/response schemas for the API."""

from pydantic import BaseModel, Field, model_validator

from claude_review.domain.models import (
    CommentSeverity,
    DiffFile,
    LineSide,
    ReviewMode,
    RoundSubmission,
    ThreadQuestion,
    TurnAuthor,
)


class DiffResponse(BaseModel):
    """Response for GET /api/diff."""

    files: list[DiffFile]
    mode: ReviewMode
    title: str
    # Which round is being written, and whether anything is there to answer
    # it. A review reloaded mid-round has to learn both from somewhere.
    round: int = 1
    answerer_attached: bool = False


class TurnInput(BaseModel):
    """One turn of a thread, as the browser sends it back."""

    author: TurnAuthor
    body: str = Field(min_length=1, max_length=50_000)
    round: int = Field(default=1, ge=1)


class CommentInput(BaseModel):
    """A single comment in the submit request."""

    # A newline in a path would let a filename write its own heading in the
    # review — a whole fabricated section, blocker and all, in what the agent
    # reads. Git quotes such names, and the parser faithfully decodes them.
    file: str = Field(min_length=1, pattern=r"^[^\x00-\x1f\x7f]+$")
    side: LineSide
    severity: CommentSeverity
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    body: str = Field(min_length=1, max_length=50_000)
    turns: list[TurnInput] = Field(default_factory=list, max_length=200)
    resolved: bool = False
    outdated: bool = False
    # What the thread was written against, kept for when those lines are gone
    quote: list[str] = Field(default_factory=list, max_length=200)

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
    # Whether this send is the last one. False sends a round and leaves the
    # review open, which only makes sense while something is answering it.
    end: bool = True


class SubmitResponse(BaseModel):
    """Response for POST /api/submit."""

    markdown: str
    comment_count: int
    # Which round was just sent, and which one is being written now
    round: int
    ended: bool


class RoundResponse(BaseModel):
    """Response for POST /api/round — the diff taken again."""

    file_count: int
    round: int


class FileWindowResponse(BaseModel):
    """Response for GET /api/file-window."""

    start: int
    lines: list[str]
    total: int


class AskRequest(BaseModel):
    """Request body for POST /api/ask — the reader asking about a thread."""

    thread_id: str = Field(min_length=1, max_length=200)
    question_id: str = Field(min_length=1, max_length=200)
    file: str = Field(min_length=1)
    side: LineSide
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    quote: list[str] = Field(default_factory=list, max_length=200)
    body: str = Field(min_length=1, max_length=50_000)
    history: list[TurnInput] = Field(default_factory=list, max_length=200)


class ReplyRequest(BaseModel):
    """Request body for POST /api/reply — the answer coming back."""

    thread_id: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=50_000)
    # Which question is being answered. Omitted, the answer goes to the
    # oldest question in that thread still waiting for one.
    question_id: str | None = Field(default=None, max_length=200)


class EventResponse(BaseModel):
    """Response for GET /api/events, the long poll an answerer waits on."""

    type: str
    question: ThreadQuestion | None = None
    round: RoundSubmission | None = None

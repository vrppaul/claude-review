"""Pydantic request/response schemas for the API."""

from pydantic import BaseModel, Field, model_validator

from claude_review.domain.models import (
    AgentStatus,
    CommentSeverity,
    DiffFile,
    LineSide,
    PanelCancel,
    PanelMessage,
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
    # What the agent last said about itself, so a reloaded review does not
    # lose the model and the context along with the pushes it missed
    agent: AgentStatus = AgentStatus()


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
    # Who opened the thread. The browser sends it back so a thread the author
    # raised is not read as something the reader wrote.
    raised_by: TurnAuthor = TurnAuthor.READER
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


class ThreadInput(BaseModel):
    """A thread as the browser hands it over, for a panel message to carry.

    The browser holds the threads — they are unsent work, and never reach
    this side until a round is — so a message pointing at one sends it
    along. What arrives is the thread as it stands right now.
    """

    thread_id: str = Field(min_length=1, max_length=200)
    file: str = Field(min_length=1)
    side: LineSide
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    quote: list[str] = Field(default_factory=list, max_length=200)
    body: str = Field(min_length=1, max_length=50_000)
    history: list[TurnInput] = Field(default_factory=list, max_length=200)


class MessageRequest(BaseModel):
    """Request body for POST /api/message — the reader typing in the panel."""

    message_id: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=50_000)
    threads: list[ThreadInput] = Field(default_factory=list, max_length=50)


class PointRequest(BaseModel):
    """Request body for POST /api/point — the author raising a thread.

    The same anchor a reader's comment carries, because it becomes exactly
    that: a thread on a line, which the reader answers, settles or removes.
    """

    file: str = Field(min_length=1, pattern=r"^[^\x00-\x1f\x7f]+$")
    side: LineSide = LineSide.NEW
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    body: str = Field(min_length=1, max_length=50_000)
    severity: CommentSeverity = CommentSeverity.NOTE

    @model_validator(mode="after")
    def start_before_end(self) -> PointRequest:
        if self.start_line > self.end_line:
            msg = "start_line must be <= end_line"
            raise ValueError(msg)
        return self


class PointResponse(BaseModel):
    """Response for POST /api/point — which thread was raised."""

    thread_id: str


class SayRequest(BaseModel):
    """Request body for POST /api/say — the agent speaking in the panel.

    Usually an answer, and then it names what it answers. It may also be the
    agent speaking first — having finished something, or having found
    something worth saying — and then there is nothing to name.
    """

    message_id: str | None = Field(default=None, max_length=200)
    text: str = Field(min_length=1, max_length=50_000)
    # Files worth opening at what was said. They travel as chips under the
    # turn, so the reader jumps rather than searches.
    files: list[str] = Field(default_factory=list, max_length=20)


class ProgressRequest(BaseModel):
    """Request body for POST /api/progress — what is being done right now.

    It replaces whatever was showing rather than adding to it: this is the
    state of the work, not a log of it. Sent empty, it says the work is over
    and the line goes away.
    """

    message_id: str | None = Field(default=None, max_length=200)
    text: str = Field(default="", max_length=500)
    files: list[str] = Field(default_factory=list, max_length=20)


class ShowRequest(BaseModel):
    """Request body for POST /api/show — bring a file into view.

    The one thing here that moves the reader's screen, so it is only ever
    sent when they asked to be taken somewhere.
    """

    file: str = Field(min_length=1, pattern=r"^[^\x00-\x1f\x7f]+$")


class CancelRequest(BaseModel):
    """Request body for POST /api/cancel — the reader taking it back."""

    message_id: str = Field(min_length=1, max_length=200)


class StatusRequest(BaseModel):
    """Request body for POST /api/status — what only the agent knows.

    Both are free text on purpose: how an agent measures its own context is
    its business, and this side only repeats it with a time beside it.
    """

    model: str | None = Field(default=None, max_length=200)
    context: str | None = Field(default=None, max_length=200)


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
    message: PanelMessage | None = None
    cancel: PanelCancel | None = None

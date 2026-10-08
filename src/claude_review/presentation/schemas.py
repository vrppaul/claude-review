"""Pydantic request/response schemas for the API."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from claude_review.domain.models import (
    AgentStatus,
    Anchor,
    AnchorKind,
    CommentSeverity,
    DiffFile,
    DiffLayout,
    GuideState,
    LineSide,
    PanelCancel,
    PanelEntry,
    PanelMessage,
    ReaderSettings,
    ReviewMode,
    ReviewVersion,
    RoundSubmission,
    Theme,
    ThreadContext,
    ThreadQuestion,
    TurnAuthor,
)
from claude_review.services.image_service import MAX_IMAGE_BYTES, MAX_IMAGES_PER_MESSAGE

# Ids handed out by POST /api/images, as many as one thing said may carry
ImageIds = Annotated[
    list[Annotated[str, Field(min_length=1, max_length=200)]],
    Field(max_length=MAX_IMAGES_PER_MESSAGE),
]


def _require_words_or_images(words: str, images: list[str]) -> None:
    """A screenshot can be the whole of what is said, but something has to be.

    Raises:
        ValueError: if there are neither words nor images.
    """
    if not words.strip() and not images:
        msg = "needs text or an image"
        raise ValueError(msg)


class ImageLimits(BaseModel):
    """The limits the browser checks before uploading an image.

    Told by the server rather than repeated in the browser, so the two
    cannot drift apart.
    """

    max_image_bytes: int = MAX_IMAGE_BYTES
    max_images_per_message: int = MAX_IMAGES_PER_MESSAGE


class DiffResponse(BaseModel):
    """Response for GET /api/diff."""

    files: list[DiffFile]
    mode: ReviewMode
    title: str
    # What the diff is compared against, as the header's control says it.
    # None in a review whose content did not come from a repository.
    phrase: str | None = None
    # Which round is being written, and whether anything is there to answer
    # it. A review reloaded mid-round has to learn both from somewhere.
    round: int = 1
    answerer_attached: bool = False
    # How many files have moved on since this diff was taken. A push says it
    # once; this is how a review that was reloaded, or opened late, finds out.
    moved: int = 0
    # What the agent last said about itself, so a reloaded review does not
    # lose the model and the context along with the pushes it missed
    agent: AgentStatus = AgentStatus()
    # What the browser checks before uploading an image
    image_limits: ImageLimits = ImageLimits()
    # Which release is serving the review, so the browser can tell a reader
    # what changed since the one they last saw. "Release" rather than
    # "version": a version here is a base the diff is read against.
    release: str


# The most threads one review hands over at once. A review with more is
# not a review any more, and the requests that carry them stay bounded.
MAX_THREADS = 500

# A release number, generously: 1.5.0, 1.5.0rc1, 1.4.3.dev0
MAX_RELEASE_LENGTH = 50

# What a file path may hold. A newline in one would let a filename write its
# own heading in the review — a whole fabricated section, blocker and all, in
# what the agent reads. Git quotes such names, and the parser faithfully
# decodes them.
SAFE_PATH = r"^[^\x00-\x1f\x7f]+$"


class LineAnchorInput(BaseModel):
    """Lines a thread hangs on, as the browser sends them."""

    kind: Literal[AnchorKind.LINE] = AnchorKind.LINE
    file: str = Field(min_length=1, pattern=SAFE_PATH)
    side: LineSide
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    # What the thread was written against, kept for when those lines are gone
    quote: list[str] = Field(default_factory=list, max_length=200)
    outdated: bool = False

    @model_validator(mode="after")
    def start_before_end(self) -> LineAnchorInput:
        if self.start_line > self.end_line:
            msg = "start_line must be <= end_line"
            raise ValueError(msg)
        return self


# One input per kind of `Anchor`
type AnchorInput = LineAnchorInput


class TurnInput(BaseModel):
    """One turn of a thread, as the browser sends it back."""

    author: TurnAuthor
    body: str = Field(max_length=50_000)
    round: int = Field(default=1, ge=1)
    images: ImageIds = Field(default_factory=list)

    @model_validator(mode="after")
    def says_something(self) -> TurnInput:
        _require_words_or_images(self.body, self.images)
        return self


class CommentInput(BaseModel):
    """A single comment in the submit request."""

    anchor: AnchorInput
    severity: CommentSeverity
    body: str = Field(max_length=50_000)
    images: ImageIds = Field(default_factory=list)
    turns: list[TurnInput] = Field(default_factory=list, max_length=200)
    # Who opened the thread. The browser sends it back so a thread the author
    # raised is not read as something the reader wrote.
    raised_by: TurnAuthor = TurnAuthor.READER
    resolved: bool = False

    @model_validator(mode="after")
    def says_something(self) -> CommentInput:
        _require_words_or_images(self.body, self.images)
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


class VersionsResponse(BaseModel):
    """Response for GET /api/versions — what the working tree can be read against."""

    versions: list[ReviewVersion]


class RoundResponse(BaseModel):
    """Response for POST /api/round — the diff taken again.

    The files that changed are named, so an agent that has come back to a
    review it left knows which ones to read again rather than all of them,
    and `since` says which round they are counted from. Both are None when
    this review kept no tree to compare against.
    """

    file_count: int
    round: int
    changed: list[str] | None = None
    since: int | None = None


class FileWindowResponse(BaseModel):
    """Response for GET /api/file-window."""

    start: int
    lines: list[str]
    total: int


class AskRequest(BaseModel):
    """Request body for POST /api/ask — the reader asking about a thread."""

    thread_id: str = Field(min_length=1, max_length=200)
    question_id: str = Field(min_length=1, max_length=200)
    anchor: AnchorInput
    body: str = Field(max_length=50_000)
    images: ImageIds = Field(default_factory=list)
    history: list[TurnInput] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def says_something(self) -> AskRequest:
        _require_words_or_images(self.body, self.images)
        return self


class ThreadInput(BaseModel):
    """A thread as the browser hands it over, for a panel message to carry.

    The browser holds the threads — they are unsent work, and never reach
    this side until a round is — so a message pointing at one sends it
    along. What arrives is the thread as it stands right now.
    """

    thread_id: str = Field(min_length=1, max_length=200)
    anchor: AnchorInput
    body: str = Field(max_length=50_000)
    images: ImageIds = Field(default_factory=list)
    history: list[TurnInput] = Field(default_factory=list, max_length=200)
    severity: CommentSeverity = CommentSeverity.NOTE
    resolved: bool = False
    raised_by: TurnAuthor = TurnAuthor.READER

    @model_validator(mode="after")
    def says_something(self) -> ThreadInput:
        _require_words_or_images(self.body, self.images)
        return self


class SessionHello(BaseModel):
    """What the browser says on connecting, and whenever its threads change.

    The review on screen is the only side that knows what has been written
    in it — the threads are unsent work — and the only side that survives a
    server restarted mid-review. So it says both, and neither costs anybody
    anything: this never leaves the machine until an agent asks for it.
    """

    round: int | None = Field(default=None, ge=1)
    threads: list[ThreadInput] = Field(default_factory=list, max_length=MAX_THREADS)


class ContextResponse(BaseModel):
    """Response for GET /api/context — the review as it stands.

    An index, not the contents: one line's worth per thread, and the panel
    in short. Whoever wants a thread in full asks for that thread.
    """

    title: str
    round: int
    file_count: int
    answerer_attached: bool
    agent: AgentStatus
    threads: list[ThreadContext]
    panel: list[PanelEntry]


class MessageRequest(BaseModel):
    """Request body for POST /api/message — the reader typing in the panel."""

    message_id: str = Field(min_length=1, max_length=200)
    # May be empty when an image is attached: a screenshot can be the whole
    # question
    text: str = Field(default="", max_length=50_000)
    threads: list[ThreadInput] = Field(default_factory=list, max_length=50)
    images: ImageIds = Field(default_factory=list)

    @model_validator(mode="after")
    def says_something(self) -> MessageRequest:
        _require_words_or_images(self.text, self.images)
        return self


class ImageResponse(BaseModel):
    """Response for POST /api/images — what the image is kept under."""

    image_id: str


class PointRequest(BaseModel):
    """Request body for POST /api/point — the author raising a thread.

    The same anchor a reader's comment carries, because it becomes exactly
    that: a thread on a line, which the reader answers, settles or removes.
    """

    file: str = Field(min_length=1, pattern=SAFE_PATH)
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


class FollowRequest(BaseModel):
    """Request body for POST /api/anchors/follow — where these are now.

    The browser holds the threads, and the server holds the diff they hang
    on: after a round the browser sends what its threads hang on, and gets
    each one back moved onto the diff as it now stands, in the same order.
    """

    anchors: list[AnchorInput] = Field(max_length=MAX_THREADS)


class FollowResponse(BaseModel):
    """Response for POST /api/anchors/follow, one anchor per one asked about."""

    anchors: list[Anchor]


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


class ProgressStep(BaseModel):
    """One branch of the work: something being done, or something done."""

    text: str = Field(min_length=1, max_length=200)
    done: bool = False


class ProgressRequest(BaseModel):
    """Request body for POST /api/progress — what is being done right now.

    It replaces whatever was showing rather than adding to it: this is the
    state of the work, not a log of it. Sent empty, it says the work is over
    and the line goes away.
    """

    message_id: str | None = Field(default=None, max_length=200)
    text: str = Field(default="", max_length=500)
    files: list[str] = Field(default_factory=list, max_length=20)
    # What the work has branched into: subagents, checks, files being
    # rewritten. Sent whole every time, because this is a state and not a log.
    steps: list[ProgressStep] = Field(default_factory=list, max_length=20)


class ShowRequest(BaseModel):
    """Request body for POST /api/show — bring a file into view.

    The one thing here that moves the reader's screen, so it is only ever
    sent when they asked to be taken somewhere.
    """

    file: str = Field(min_length=1, pattern=SAFE_PATH)


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


class SettingsResponse(BaseModel):
    """Response for GET /api/settings."""

    settings: ReaderSettings
    # Whether anything has been kept yet. A browser still holding choices
    # made before they moved to the server hands them over once, when not.
    stored: bool


class SettingsChange(BaseModel):
    """Request body for PUT /api/settings — the choices being changed, and only those."""

    model_config = ConfigDict(extra="forbid")

    theme: Theme | None = None
    diff_layout: DiffLayout | None = None
    ignore_whitespace: bool | None = None
    sound_on_replies: bool | None = None


class GuideResponse(BaseModel):
    """Response for GET /api/guide."""

    guide: GuideState
    stored: bool


class GuideChange(BaseModel):
    """Request body for PUT /api/guide."""

    model_config = ConfigDict(extra="forbid")

    seen_release: str = Field(min_length=1, max_length=MAX_RELEASE_LENGTH)

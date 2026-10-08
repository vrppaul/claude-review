"""Pydantic request/response schemas for the API."""

from enum import StrEnum, auto
from typing import Annotated, Literal, Self

from pydantic import ConfigDict, Field, model_validator

from claude_review.domain.models import (
    AgentStatus,
    Anchor,
    ChangesSince,
    CommentSeverity,
    DiffFile,
    DiffLayout,
    FilePath,
    GuideState,
    PanelCancel,
    PanelEntry,
    PanelMessage,
    ReaderSettings,
    ReviewMode,
    ReviewModel,
    ReviewVersion,
    RoundSubmission,
    Theme,
    Thread,
    ThreadQuestion,
    TurnAuthor,
)
from claude_review.services.image_service import MAX_IMAGE_BYTES, MAX_IMAGES_PER_MESSAGE

# The most one thing said may hold: a comment, a turn, a panel message
MAX_TEXT_LENGTH = 50_000

# The longest id a request may name: a thread, a question, a message, an
# image, a base
MAX_ID_LENGTH = 200

# How long an agent's poll for events waits when it does not say: long enough
# that a loop of polls costs nothing, short enough to stay under the timeouts
# of whatever runs the command
DEFAULT_WAIT_SECONDS = 25.0
# The longest one poll may wait, so a caller that asks for more is told so
# rather than left holding a connection for good
MAX_WAIT_SECONDS = 600.0

# Ids handed out by POST /api/images, as many as one thing said may carry
ImageIds = Annotated[
    list[Annotated[str, Field(min_length=1, max_length=MAX_ID_LENGTH)]],
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


class ImageLimits(ReviewModel):
    """The limits the browser checks before uploading an image.

    Told by the server rather than repeated in the browser, so the two
    cannot drift apart.
    """

    max_image_bytes: int = MAX_IMAGE_BYTES
    max_images_per_message: int = MAX_IMAGES_PER_MESSAGE


class DiffResponse(ReviewModel):
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


# The most turns one thread carries
MAX_TURNS = 200

# The most threads one panel message may point at
MAX_THREADS_IN_MESSAGE = 50

# The most threads one review hands over at once. A review with more is
# not a review any more, and the requests that carry them stay bounded.
MAX_THREADS = 500

# The most files one thing the agent says may hang off it, as chips
MAX_FILES_NAMED = 20

# A release number, generously: 1.5.0, 1.5.0rc1, 1.4.3.dev0
MAX_RELEASE_LENGTH = 50


class SaysSomething(ReviewModel):
    """Something said: words, screenshots, or both — but never neither."""

    body: str = Field(max_length=MAX_TEXT_LENGTH)
    images: ImageIds = Field(default_factory=list)

    @model_validator(mode="after")
    def says_something(self) -> Self:
        _require_words_or_images(self.body, self.images)
        return self


class TurnInput(SaysSomething):
    """One turn of a thread, as the browser sends it back."""

    author: TurnAuthor
    round: int = Field(ge=1)


class ThreadInput(SaysSomething):
    """A thread as the browser holds it, turns and all.

    The browser holds the threads — they are unsent work, and never reach
    this side until a round is — so whatever is about one sends it along,
    as it stands right now: a round, a question, a panel message, the
    review saying what it holds.
    """

    thread_id: str = Field(min_length=1, max_length=MAX_ID_LENGTH)
    anchor: Anchor
    severity: CommentSeverity
    turns: list[TurnInput] = Field(default_factory=list, max_length=MAX_TURNS)
    # Who opened it. Sent back so a thread the author raised is not read as
    # something the reader wrote.
    raised_by: TurnAuthor
    resolved: bool


class SubmitRequest(ReviewModel):
    """Request body for POST /api/submit."""

    threads: list[ThreadInput] = Field(max_length=MAX_THREADS)
    body: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    # Whether this send is the last one. False sends a round and leaves the
    # review open, which only makes sense while something is answering it.
    end: bool


class SubmitResponse(ReviewModel):
    """Response for POST /api/submit."""

    markdown: str
    comment_count: int
    # Which round was just sent, and which one is being written now
    round: int
    ended: bool


class VersionsResponse(ReviewModel):
    """Response for GET /api/versions — what the working tree can be read against."""

    versions: list[ReviewVersion]


class RoundResponse(ReviewModel):
    """Response for POST /api/round — the diff taken again.

    The files that changed are named, so an agent that has come back to a
    review it left knows which ones to read again rather than all of them.
    None when this review kept no tree to compare against.
    """

    file_count: int
    round: int
    changes: ChangesSince | None


class FileWindowResponse(ReviewModel):
    """Response for GET /api/file-window."""

    start: int
    lines: list[str]
    total: int


class AskRequest(ReviewModel):
    """Request body for POST /api/ask — the reader asking in a thread.

    The whole thread goes, as it stands: what is asked is the reader's last
    word in it, or the comment that opened it, and the server works that
    out rather than being told it twice.
    """

    question_id: str = Field(min_length=1, max_length=MAX_ID_LENGTH)
    thread: ThreadInput


class SessionHello(ReviewModel):
    """What the browser says on connecting, and whenever its threads change.

    The review on screen is the only side that knows what has been written
    in it — the threads are unsent work — and the only side that survives a
    server restarted mid-review. So it says both, and neither costs anybody
    anything: this never leaves the machine until an agent asks for it.
    """

    round: int | None = Field(default=None, ge=1)
    # None when the browser said nothing about them; an empty list when it
    # holds none — the last one was deleted
    threads: list[ThreadInput] | None = Field(default=None, max_length=MAX_THREADS)


class ContextResponse(ReviewModel):
    """Response for GET /api/context — the review as it stands.

    An index, not the contents: one line's worth per thread, and the panel
    in short. Whoever wants a thread in full asks for that thread.
    """

    title: str
    round: int
    file_count: int
    answerer_attached: bool
    agent: AgentStatus
    threads: list[Thread]
    panel: list[PanelEntry]


class MessageRequest(ReviewModel):
    """Request body for POST /api/message — the reader typing in the panel."""

    message_id: str = Field(min_length=1, max_length=MAX_ID_LENGTH)
    # May be empty when an image is attached: a screenshot can be the whole
    # question
    text: str = Field(default="", max_length=MAX_TEXT_LENGTH)
    threads: list[ThreadInput] = Field(default_factory=list, max_length=MAX_THREADS_IN_MESSAGE)
    images: ImageIds = Field(default_factory=list)

    @model_validator(mode="after")
    def says_something(self) -> MessageRequest:
        _require_words_or_images(self.text, self.images)
        return self


class ImageResponse(ReviewModel):
    """Response for POST /api/images — what the image is kept under."""

    image_id: str


class PointRequest(ReviewModel):
    """Request body for POST /api/point — the author raising a thread.

    The same anchor a reader's comment carries, because it becomes exactly
    that: a thread on a line, which the reader answers, settles or removes.
    """

    anchor: Anchor
    body: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    severity: CommentSeverity


class FollowRequest(ReviewModel):
    """Request body for POST /api/anchors/follow — where these are now.

    The browser holds the threads, and the server holds the diff they hang
    on: after a round the browser sends what its threads hang on, and gets
    each one back moved onto the diff as it now stands, in the same order.
    """

    anchors: list[Anchor] = Field(max_length=MAX_THREADS)


class FollowResponse(ReviewModel):
    """Response for POST /api/anchors/follow, one anchor per one asked about."""

    anchors: list[Anchor]


class PointResponse(ReviewModel):
    """Response for POST /api/point — which thread was raised."""

    thread_id: str


class SayRequest(ReviewModel):
    """Request body for POST /api/say — the agent speaking in the panel.

    Usually an answer, and then it names what it answers. It may also be the
    agent speaking first — having finished something, or having found
    something worth saying — and then there is nothing to name.
    """

    message_id: str | None = Field(default=None, max_length=MAX_ID_LENGTH)
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    # Files worth opening at what was said. They travel as chips under the
    # turn, so the reader jumps rather than searches.
    files: list[FilePath] = Field(default_factory=list, max_length=MAX_FILES_NAMED)


# The longest one branch of the work may be said in: a line, not a report
MAX_STEP_LENGTH = 200

# The longest what is being done may be said in. It is a state that replaces
# itself, not a log, so a line or two is all it ever needs.
MAX_PROGRESS_LENGTH = 500

# The most branches the work is shown as at once
MAX_PROGRESS_STEPS = 20


class ProgressStep(ReviewModel):
    """One branch of the work: something being done, or something done."""

    text: str = Field(min_length=1, max_length=MAX_STEP_LENGTH)
    done: bool = False


class ProgressRequest(ReviewModel):
    """Request body for POST /api/progress — what is being done right now.

    It replaces whatever was showing rather than adding to it: this is the
    state of the work, not a log of it. Sent empty, it says the work is over
    and the line goes away.
    """

    message_id: str | None = Field(default=None, max_length=MAX_ID_LENGTH)
    text: str = Field(default="", max_length=MAX_PROGRESS_LENGTH)
    files: list[FilePath] = Field(default_factory=list, max_length=MAX_FILES_NAMED)
    # What the work has branched into: subagents, checks, files being
    # rewritten. Sent whole every time, because this is a state and not a log.
    steps: list[ProgressStep] = Field(default_factory=list, max_length=MAX_PROGRESS_STEPS)


class ShowRequest(ReviewModel):
    """Request body for POST /api/show — bring a file into view.

    The one thing here that moves the reader's screen, so it is only ever
    sent when they asked to be taken somewhere.
    """

    file: FilePath


class CancelRequest(ReviewModel):
    """Request body for POST /api/cancel — the reader taking it back."""

    message_id: str = Field(min_length=1, max_length=MAX_ID_LENGTH)


# The longest the agent may say which model it is, or how full its context is
MAX_STATUS_LENGTH = 200


class StatusRequest(ReviewModel):
    """Request body for POST /api/status — what only the agent knows.

    Both are free text on purpose: how an agent measures its own context is
    its business, and this side only repeats it with a time beside it.
    """

    model: str | None = Field(default=None, max_length=MAX_STATUS_LENGTH)
    context: str | None = Field(default=None, max_length=MAX_STATUS_LENGTH)


class ReplyRequest(ReviewModel):
    """Request body for POST /api/reply — the answer coming back."""

    thread_id: str = Field(min_length=1, max_length=MAX_ID_LENGTH)
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    # Which question is being answered. Omitted, the answer goes to the
    # oldest question in that thread still waiting for one.
    question_id: str | None = Field(default=None, max_length=MAX_ID_LENGTH)


class EventKind(StrEnum):
    """What GET /api/events can answer, as the `type` the agent's loop reads.

    QUESTION — a question asked in one thread.
    ROUND — a round of the review, sent.
    MESSAGE — something typed in the agent panel.
    CANCEL — a panel message taken back.
    TIMEOUT — nothing was handed over in the time asked for.
    CLOSED — the review is over, and nothing handed over is left.
    """

    QUESTION = auto()
    ROUND = auto()
    MESSAGE = auto()
    CANCEL = auto()
    TIMEOUT = auto()
    CLOSED = auto()


class QuestionEvent(ReviewModel):
    type: Literal[EventKind.QUESTION] = EventKind.QUESTION
    question: ThreadQuestion


class RoundEvent(ReviewModel):
    type: Literal[EventKind.ROUND] = EventKind.ROUND
    round: RoundSubmission


class MessageEvent(ReviewModel):
    type: Literal[EventKind.MESSAGE] = EventKind.MESSAGE
    message: PanelMessage


class CancelEvent(ReviewModel):
    type: Literal[EventKind.CANCEL] = EventKind.CANCEL
    cancel: PanelCancel


class TimeoutEvent(ReviewModel):
    type: Literal[EventKind.TIMEOUT] = EventKind.TIMEOUT


class ClosedEvent(ReviewModel):
    type: Literal[EventKind.CLOSED] = EventKind.CLOSED


# Response for GET /api/events, the long poll an answerer waits on: one kind
# of event, carrying only what that kind is
type EventResponse = Annotated[
    QuestionEvent | RoundEvent | MessageEvent | CancelEvent | TimeoutEvent | ClosedEvent,
    Field(discriminator="type"),
]


class SettingsResponse(ReviewModel):
    """Response for GET /api/settings."""

    settings: ReaderSettings
    # Whether anything has been kept yet. A browser still holding choices
    # made before they moved to the server hands them over once, when not.
    stored: bool


class SettingsChange(ReviewModel):
    """Request body for PUT /api/settings — the choices being changed, and only those."""

    model_config = ConfigDict(extra="forbid")

    theme: Theme | None = None
    diff_layout: DiffLayout | None = None
    ignore_whitespace: bool | None = None
    sound_on_replies: bool | None = None


class GuideResponse(ReviewModel):
    """Response for GET /api/guide."""

    guide: GuideState
    stored: bool


class GuideChange(ReviewModel):
    """Request body for PUT /api/guide."""

    model_config = ConfigDict(extra="forbid")

    seen_release: str = Field(min_length=1, max_length=MAX_RELEASE_LENGTH)


class PushKind(StrEnum):
    """What the server pushes down the session socket, as the `type` the browser reads.

    REPLY — an answer in a thread.
    ANSWERER — whether anything is waiting to answer.
    CHAT — the agent speaking in the panel.
    PROGRESS — what the agent is doing right now.
    SHOW — bring a file into view.
    STATUS — what the agent said about itself.
    POINT — a thread the agent raised on a line.
    CHANGED — the working tree moved away from the diff on screen.
    ROUND — the round now being written.
    DIFF — the diff was taken again.
    """

    REPLY = auto()
    ANSWERER = auto()
    CHAT = auto()
    PROGRESS = auto()
    SHOW = auto()
    STATUS = auto()
    POINT = auto()
    CHANGED = auto()
    ROUND = auto()
    DIFF = auto()


class ReplyPush(ReviewModel):
    """An answer to one thread, and which question in it, when the answer says."""

    type: Literal[PushKind.REPLY] = PushKind.REPLY
    thread_id: str
    question_id: str | None
    text: str


class AnswererPush(ReviewModel):
    type: Literal[PushKind.ANSWERER] = PushKind.ANSWERER
    attached: bool


class ChatPush(ReviewModel):
    """The agent speaking in the panel: an answer to a message, or nothing answered at all."""

    type: Literal[PushKind.CHAT] = PushKind.CHAT
    message_id: str | None
    text: str
    files: list[FilePath]


class ProgressPush(ReviewModel):
    """What the agent is doing right now, whole: it replaces whatever was showing."""

    type: Literal[PushKind.PROGRESS] = PushKind.PROGRESS
    message_id: str | None
    text: str
    files: list[FilePath]
    steps: list[ProgressStep]

    def says_nothing(self) -> bool:
        """Whether this says the work is over, rather than what it is."""
        return not self.text.strip() and not self.steps


class ShowPush(ReviewModel):
    type: Literal[PushKind.SHOW] = PushKind.SHOW
    file: FilePath


class StatusPush(ReviewModel):
    type: Literal[PushKind.STATUS] = PushKind.STATUS
    agent: AgentStatus


class PointPush(ReviewModel):
    """A thread the agent raised, quoted from the diff it was checked against."""

    type: Literal[PushKind.POINT] = PushKind.POINT
    thread_id: str
    anchor: Anchor
    body: str
    severity: CommentSeverity


class ChangedPush(ReviewModel):
    """How many files have moved since the diff on screen was taken. Said, never acted on."""

    type: Literal[PushKind.CHANGED] = PushKind.CHANGED
    moved_count: int


class RoundPush(ReviewModel):
    """The round now being written, after one was sent and the review stayed open."""

    type: Literal[PushKind.ROUND] = PushKind.ROUND
    number: int


class DiffPush(ReviewModel):
    """The diff was taken again: fetch it, and which files changed since the round began."""

    type: Literal[PushKind.DIFF] = PushKind.DIFF
    changes: ChangesSince | None


# What the server pushes down the session socket, told apart by `type`
type ServerPush = Annotated[
    ReplyPush
    | AnswererPush
    | ChatPush
    | ProgressPush
    | ShowPush
    | StatusPush
    | PointPush
    | ChangedPush
    | RoundPush
    | DiffPush,
    Field(discriminator="type"),
]

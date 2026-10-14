"""What passes between the review and its agent: what the reader handed over, and what the agent says back."""

from enum import StrEnum, auto
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AfterValidator, Field

from claude_review.domain import models
from claude_review.domain.models import EpochMillis, FilePath, StepText, TurnAuthor
from claude_review.presentation.wire.base import (
    MAX_FILES_NAMED,
    MAX_TEXT_LENGTH,
    AgentText,
    LinesWritten,
    WireBool,
    WireId,
    WireModel,
)
from claude_review.presentation.wire.threads import SaysSomething, Thread, ThreadInput, ThreadSummary

# The most threads one panel message may point at
MAX_THREADS_IN_MESSAGE = 50

# The longest what is being done may be said in. It is a state that replaces
# itself, not a log, so a line or two is all it ever needs.
MAX_PROGRESS_LENGTH = 500

# What the work is being said as, which may be nothing: the work is over
ProgressText = Annotated[str, Field(max_length=MAX_PROGRESS_LENGTH)]

# The most branches the work is shown as at once
MAX_PROGRESS_STEPS = 20

# How a refusal lists the names a list repeats
NAMES_SEPARATOR = ", "

# The longest the agent may say which model it is, or how full its context is
MAX_STATUS_LENGTH = 200
StatusText = Annotated[str, Field(max_length=MAX_STATUS_LENGTH)]


class AgentStatus(WireModel):
    """What the agent has said about itself: nothing until it reports, never a zero standing in for it."""

    model: str | None
    context: str | None
    # When it last reported, so the panel can say how old the numbers are
    at: EpochMillis | None


class ProgressStep(WireModel):
    """One branch of the work: something being done, or something done."""

    text: StepText
    done: WireBool = False

    def in_the_review(self) -> models.ProgressStep:
        return models.ProgressStep.model_validate(self, from_attributes=True)


def _refuse_repeats(names: list[str]) -> None:
    """Refuse a list that names anything more than once, naming what it repeats.

    Raises:
        ValueError: if a name comes again after its first time.
    """
    repeated = dict.fromkeys(name for position, name in enumerate(names) if name in names[:position])
    if repeated:
        msg = f"names {NAMES_SEPARATOR.join(repeated)} more than once"
        raise ValueError(msg)


def _each_file_once(files: list[str]) -> list[str]:
    _refuse_repeats(files)
    return files


def _each_branch_once(steps: list[ProgressStep]) -> list[ProgressStep]:
    _refuse_repeats([step.text for step in steps])
    return steps


# Files hung off what the agent says, a chip each the reader can jump by. Each
# once: the page tells the chips apart by their paths, and a second chip for a
# file says nothing the first did not.
NamedFiles = Annotated[list[FilePath], Field(max_length=MAX_FILES_NAMED), AfterValidator(_each_file_once)]

# What the work has branched into, each branch once: the reader tells them
# apart by what they say, and so does the page
WorkBranches = Annotated[list[ProgressStep], Field(max_length=MAX_PROGRESS_STEPS), AfterValidator(_each_branch_once)]


class AgentWork(WireModel):
    """What the agent is doing right now, whole: it replaces whatever was showing."""

    # Which message the work is for; None for work on the agent's own account
    message_id: str | None
    text: str
    files: list[FilePath]
    steps: list[ProgressStep]
    # When it was reported, so a review reloaded later says how long it has gone on
    at: EpochMillis


class ThreadQuestion(WireModel):
    """Something the reader asked in one thread, with the whole thread around it."""

    # Which question in that thread: an answer has to say which it belongs to
    question_id: str
    # What is asked: the reader's last word in the thread, or the comment that opened it
    body: str
    images: list[Path]
    thread: Thread


class PanelMessage(WireModel):
    """Something the reader typed in the agent panel, with the threads it points at."""

    message_id: str
    body: str
    threads: list[Thread]
    images: list[Path]


class PanelCancel(WireModel):
    """The reader withdrawing a panel message before it was answered."""

    message_id: str


class PanelEntry(WireModel):
    """One thing said in the panel, as an agent catching up reads it: its screenshots as files to open."""

    message_id: str | None
    author: TurnAuthor
    body: str
    at: EpochMillis
    images: list[Path]


class SaidInPanel(WireModel):
    """One thing said in the panel, as a page draws it: the reader's message, or the agent's words."""

    # What every page knows it by: a message's own id, or the one the agent's words were pushed under
    said_id: str
    # The message it is, or the one the agent answers; None when the agent spoke first
    message_id: str | None
    author: TurnAuthor
    body: str
    at: EpochMillis
    # Screenshots pasted with a message, by the ids GET /api/images/{image_id} serves them under
    images: list[str]
    # The threads a message points at, by their ids
    threads: list[str]
    # Files the agent's words name, a chip each
    files: list[FilePath]
    # Whether the reader took the message back before it was answered
    taken_back: WireBool


class ConversationResponse(WireModel):
    """Response for GET /api/conversation — what was said in the panel, for a page opening to draw.

    Everything the review heard, oldest first: what was said before any page
    was open, and what a page in another browser saw. Read once, as the page
    opens; from then on what the agent says is pushed, under the same ids.
    """

    said: list[SaidInPanel]


class RoundSubmission(WireModel):
    """One round of a review, on its way to whoever answers it."""

    number: int
    markdown: str
    comment_count: int


class CatchUpResponse(WireModel):
    """Response for GET /api/catch-up — the review as it stands.

    An index, not the contents: one line's worth per thread, and the panel
    in short. Whoever wants a thread in full reads that thread.
    """

    title: str
    round: int
    file_count: int
    answerer_attached: WireBool
    agent: AgentStatus
    threads: list[ThreadSummary]
    panel: list[PanelEntry]


class MessageRequest(SaysSomething):
    """Request body for POST /api/message — the reader typing in the panel.

    Words, screenshots or both, like anything else said: a screenshot can be
    the whole question.
    """

    message_id: WireId
    body: str = Field(default="", max_length=MAX_TEXT_LENGTH)
    threads: list[ThreadInput] = Field(default_factory=list, max_length=MAX_THREADS_IN_MESSAGE)


class ImageResponse(WireModel):
    """Response for POST /api/images — what the image is kept under."""

    image_id: str


class SayRequest(WireModel):
    """Request body for POST /api/say — the agent speaking in the panel.

    Usually an answer, and then it names what it answers. It may also be the
    agent speaking first — having finished something, or having found
    something worth saying — and then there is nothing to name.
    """

    message_id: WireId | None = None
    body: AgentText
    # Files worth opening at what was said. They travel as chips under the
    # turn, so the reader jumps rather than searches.
    files: NamedFiles = Field(default_factory=list)


class ProgressRequest(WireModel):
    """Request body for POST /api/progress — what is being done right now.

    It replaces whatever was showing rather than adding to it: this is the
    state of the work, not a log of it. Sent empty, it says the work is over
    and the line goes away.
    """

    message_id: WireId | None = None
    text: ProgressText = ""
    files: NamedFiles = Field(default_factory=list)
    # What the work has branched into: subagents, checks, files being
    # rewritten. Sent whole every time, because this is a state and not a log.
    steps: WorkBranches = Field(default_factory=list)


class ShowRequest(WireModel):
    """Request body for POST /api/show — bring a file into view.

    The one thing here that moves the reader's screen, so it is only ever
    sent when they asked to be taken somewhere.
    """

    file: FilePath


class CancelRequest(WireModel):
    """Request body for POST /api/cancel — the reader taking it back."""

    message_id: WireId


class StatusRequest(WireModel):
    """Request body for POST /api/status — what only the agent knows.

    Both are free text on purpose: how an agent measures its own context is
    its business, and this side only repeats it with a time beside it.
    """

    model: StatusText | None = None
    context: StatusText | None = None


class ReplyRequest(WireModel):
    """Request body for POST /api/reply — the answer coming back."""

    thread_id: WireId
    body: AgentText
    # Which question is being answered. Omitted, the answer goes to the
    # oldest question in that thread still waiting for one.
    question_id: WireId | None = None


class EventKind(StrEnum):
    """What POST /api/events can answer, as the `type` the agent's loop reads.

    QUESTION — a question asked in one thread.
    ROUND — a round of the review, sent.
    MESSAGE — something typed in the agent panel.
    CANCEL — a panel message taken back.
    STORY_REQUEST — the reader asks for a story of the change.
    STORY_CANCEL — the reader stopped the story they asked for.
    TIMEOUT — nothing was handed over in the time asked for.
    CLOSED — the review is over, and nothing handed over is left.
    """

    QUESTION = auto()
    ROUND = auto()
    MESSAGE = auto()
    CANCEL = auto()
    STORY_REQUEST = auto()
    STORY_CANCEL = auto()
    TIMEOUT = auto()
    CLOSED = auto()


class QuestionEvent(WireModel):
    type: Literal[EventKind.QUESTION] = EventKind.QUESTION
    question: ThreadQuestion


class RoundEvent(WireModel):
    type: Literal[EventKind.ROUND] = EventKind.ROUND
    round: RoundSubmission


class MessageEvent(WireModel):
    type: Literal[EventKind.MESSAGE] = EventKind.MESSAGE
    message: PanelMessage


class CancelEvent(WireModel):
    type: Literal[EventKind.CANCEL] = EventKind.CANCEL
    cancel: PanelCancel


class StaleStep(WireModel):
    """A step of the story told whose code a round changed after it was told: its chapter, its file, its lines now."""

    chapter: str
    file: str
    # Written as the agent writes a step's lines: "104-131"
    lines: LinesWritten


class StoryWentStale(WireModel):
    """What of the story the agent told a round moved the code on under."""

    # The round of the take that first found it so
    round: int
    steps: list[StaleStep]
    # How many lines the change added or removed that no step tells now
    left_out: int


class StoryRequestEvent(WireModel):
    type: Literal[EventKind.STORY_REQUEST] = EventKind.STORY_REQUEST
    # What went stale of the story told before, to tell it again; None for a first story
    stale: StoryWentStale | None = None


class StoryCancelEvent(WireModel):
    type: Literal[EventKind.STORY_CANCEL] = EventKind.STORY_CANCEL


class TimeoutEvent(WireModel):
    type: Literal[EventKind.TIMEOUT] = EventKind.TIMEOUT


class ClosedEvent(WireModel):
    type: Literal[EventKind.CLOSED] = EventKind.CLOSED


# Response for POST /api/events, the long poll an answerer waits on: one kind
# of event, carrying only what that kind is
type EventResponse = Annotated[
    QuestionEvent
    | RoundEvent
    | MessageEvent
    | CancelEvent
    | StoryRequestEvent
    | StoryCancelEvent
    | TimeoutEvent
    | ClosedEvent,
    Field(discriminator="type"),
]

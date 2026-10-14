"""What the review pushes down the session socket to every page open on it, told apart by `type`."""

from enum import StrEnum, auto
from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from claude_review.domain.models import CommentSeverity, FilePath
from claude_review.presentation.wire.agent import AgentStatus, AgentWork
from claude_review.presentation.wire.base import WireBool, WireModel
from claude_review.presentation.wire.content import ChangesSince, StoryAsking
from claude_review.presentation.wire.threads import Anchor


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
    STORY — a story was told of the change.
    STORY_ASKING — how the reader's asking for a story now stands.
    ENDED — the review is over.
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
    STORY = auto()
    STORY_ASKING = auto()
    ENDED = auto()


class Push(WireModel):
    """What every push is: said once, as it stands, and never changed."""

    model_config = ConfigDict(frozen=True)


class ReplyPush(Push):
    """An answer to one thread, and which question in it, when the answer says."""

    type: Literal[PushKind.REPLY] = PushKind.REPLY
    thread_id: str
    question_id: str | None
    body: str


class AnswererPush(Push):
    type: Literal[PushKind.ANSWERER] = PushKind.ANSWERER
    attached: WireBool


class ChatPush(Push):
    """The agent speaking in the panel: an answer to a message, or nothing answered at all."""

    type: Literal[PushKind.CHAT] = PushKind.CHAT
    # What the review holds the words under, as GET /api/conversation says them:
    # a page that read them there as it opened takes them in once
    said_id: str
    message_id: str | None
    body: str
    files: list[FilePath]


class ProgressPush(Push):
    """What the agent is doing now, or None: the work is over and its line goes away."""

    type: Literal[PushKind.PROGRESS] = PushKind.PROGRESS
    work: AgentWork | None


class ShowPush(Push):
    type: Literal[PushKind.SHOW] = PushKind.SHOW
    file: FilePath


class StatusPush(Push):
    type: Literal[PushKind.STATUS] = PushKind.STATUS
    agent: AgentStatus


class PointPush(Push):
    """A thread the agent raised, quoted from the diff it was checked against."""

    type: Literal[PushKind.POINT] = PushKind.POINT
    thread_id: str
    anchor: Anchor
    body: str
    severity: CommentSeverity


class ChangedPush(Push):
    """How many files have moved since the diff on screen was taken. Said, never acted on."""

    type: Literal[PushKind.CHANGED] = PushKind.CHANGED
    moved_count: int


class RoundPush(Push):
    """The round now being written, after one was sent and the review stayed open."""

    type: Literal[PushKind.ROUND] = PushKind.ROUND
    number: int


class DiffPush(Push):
    """The diff was taken again: fetch it. How many files the review now holds, and which changed since the round began.

    The count is the review's own: a page reading a narrower base cannot
    count the review from what it has on screen.
    """

    type: Literal[PushKind.DIFF] = PushKind.DIFF
    file_count: int
    changes: ChangesSince | None


class StoryPush(Push):
    """A story was told of the change, in place of any before it: the page fetches it.

    That there is one, and no more. The story carries the code its steps
    show, as much as the change it tells: like a diff taken again, it is
    fetched, not pushed.
    """

    type: Literal[PushKind.STORY] = PushKind.STORY


class StoryAskingPush(Push):
    """How the reader's asking for a story now stands, whole: asked, taken by an agent, or stopped.

    Pushed whole, where a story is only announced and then fetched: it is
    three values, not the code of a change.
    """

    type: Literal[PushKind.STORY_ASKING] = PushKind.STORY_ASKING
    asking: StoryAsking


class EndedPush(Push):
    """The review is over, and this is the last thing told: the page lets go of it rather than reach for it again.

    `finished`: the reader sent it for good, or ended it once everything had
    gone, and the page's draft of it is done with. Otherwise it stopped under
    them — Ctrl+C, its server stopping, a fault — and the draft is kept for
    when the review is opened again.
    """

    type: Literal[PushKind.ENDED] = PushKind.ENDED
    finished: WireBool


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
    | DiffPush
    | StoryPush
    | StoryAskingPush
    | EndedPush,
    Field(discriminator="type"),
]

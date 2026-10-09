"""What the review pushes down the session socket to every page open on it, told apart by `type`."""

from enum import StrEnum, auto
from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from claude_review.domain.models import CommentSeverity, FilePath
from claude_review.presentation.wire.agent import AgentStatus, AgentWork
from claude_review.presentation.wire.base import WireModel
from claude_review.presentation.wire.content import ChangesSince
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
    attached: bool


class ChatPush(Push):
    """The agent speaking in the panel: an answer to a message, or nothing answered at all."""

    type: Literal[PushKind.CHAT] = PushKind.CHAT
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

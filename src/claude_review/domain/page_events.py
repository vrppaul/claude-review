"""What the review tells the pages open on it, as it happens.

The mirror of `AgentEvent`: what the reader hands over goes to the agent,
and what the agent and the review do comes back to every page on screen.
Each is told once, as it stood when it happened, so none can be changed
afterwards.
"""

from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import (
    AgentStatus,
    AgentWork,
    Anchor,
    ChangesSince,
    CommentSeverity,
    FilePath,
)


class PageEventBase(BaseModel):
    """What every page event is: told once, and never changed."""

    model_config = ConfigDict(frozen=True)


class ThreadAnswered(PageEventBase):
    """An answer in one thread, and which question in it, when the answer says."""

    thread_id: str
    question_id: str | None
    body: str


class AnswererChanged(PageEventBase):
    """Whether anything is there to answer the review."""

    attached: bool


class AgentSaid(PageEventBase):
    """The agent speaking in the panel: an answer to a message, or nothing answered at all."""

    message_id: str | None
    body: str
    files: list[FilePath]


class WorkReported(PageEventBase):
    """What the agent is doing now, or None: the work is over."""

    work: AgentWork | None


class FileShown(PageEventBase):
    """A file the reader asked to be taken to."""

    file: FilePath


class StatusReported(PageEventBase):
    """What the agent said about itself."""

    agent: AgentStatus


class ThreadRaised(PageEventBase):
    """A thread the agent raised, quoted from the diff it was checked against."""

    thread_id: str
    anchor: Anchor
    body: str
    severity: CommentSeverity


class TreeMoved(PageEventBase):
    """How many files have moved since the diff on screen was taken. Said, never acted on."""

    moved_count: int


class RoundBegan(PageEventBase):
    """The round now being written, after one was sent and the review stayed open."""

    number: int


class DiffRetaken(PageEventBase):
    """The diff was taken again, and which files changed since the round began, when that can be said."""

    changes: ChangesSince | None


# Everything the review tells its pages
type PageEvent = (
    ThreadAnswered
    | AnswererChanged
    | AgentSaid
    | WorkReported
    | FileShown
    | StatusReported
    | ThreadRaised
    | TreeMoved
    | RoundBegan
    | DiffRetaken
)

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
    ChangedSinceRound,
    CommentSeverity,
    FilePath,
)
from claude_review.domain.story import StoryAsking


class PageEventBase(BaseModel):
    """What every page event is: told once, and never changed."""

    model_config = ConfigDict(frozen=True)


class ThreadAnswered(PageEventBase):
    """An answer in one thread, and which question in it, when the answer says."""

    thread_id: str
    question_id: str | None
    body: str


class ThreadHandedOver(PageEventBase):
    """A thread was handed to the agent: what of it the agent now has, which stays as the agent has it."""

    thread_id: str
    # Everything said in it, by id: its opening by the thread's own id, as a question names it, and each turn by its own
    said: list[str]


class AnswererChanged(PageEventBase):
    """Whether anything is there to answer the review."""

    attached: bool


class AgentSaid(PageEventBase):
    """The agent speaking in the panel: an answer to a message, or nothing answered at all."""

    # What the review holds the words under, which a page reading the conversation as it opens knows them by
    said_id: str
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
    """The diff was taken again: how many files it holds, and which changed since the round began, if that is known."""

    file_count: int
    changes: ChangedSinceRound | None


class StoryTold(PageEventBase):
    """A story was told of the change, in place of any told before: a page reads it from the review.

    Told that there is one, never the story itself: it carries the code its
    steps show, as much as the change it tells, and is read as a diff taken
    again is.
    """


class StoryAskingChanged(PageEventBase):
    """How the reader's asking for a story now stands: asked, taken by an agent, stopped, or ended by a story told.

    Told whole, as a fact, so a page takes it as told and asks nothing. A
    story told ends the asking: it is told after `StoryTold`, with nothing
    asked any more.
    """

    # None once a story told ended it
    asking: StoryAsking | None


class ReviewEnded(PageEventBase):
    """The review is over, and nothing more will be told.

    Finished, the reader sent it for good or ended it once everything had
    gone, and what a page holds of it is done with. Otherwise it stopped
    under them — Ctrl+C, its server stopping, a fault — and what a page has
    not sent is still theirs, for when the review is opened again.
    """

    finished: bool


# Everything the review tells its pages
type PageEvent = (
    ThreadAnswered
    | ThreadHandedOver
    | AnswererChanged
    | AgentSaid
    | WorkReported
    | FileShown
    | StatusReported
    | ThreadRaised
    | TreeMoved
    | RoundBegan
    | DiffRetaken
    | StoryTold
    | StoryAskingChanged
    | ReviewEnded
)

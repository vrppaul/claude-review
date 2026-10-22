"""What a page reads for each thing that happens in the review: one push per page event.

The review says what happened in its own words, as a domain event; the page
reads it as a push of the API. This is the one place each event becomes
its push. The match is closed by `assert_never`, so an event added to the
review without a push here fails the type check.
"""

from typing import assert_never

from claude_review.domain.page_events import (
    AgentSaid,
    AnswererChanged,
    DiffRetaken,
    FileShown,
    PageEvent,
    ReviewEnded,
    RoundBegan,
    StatusReported,
    StoryAskingChanged,
    StoryTold,
    ThreadAnswered,
    ThreadHandedOver,
    ThreadRaised,
    TreeMoved,
    WorkReported,
)
from claude_review.presentation.schemas.agent import AgentStatus, AgentWork
from claude_review.presentation.schemas.base import made_or_none
from claude_review.presentation.schemas.content import StoryAsking
from claude_review.presentation.schemas.pushes import (
    AnswererPush,
    ChangedPush,
    ChatPush,
    DiffPush,
    EndedPush,
    HandedPush,
    PointPush,
    ProgressPush,
    ReplyPush,
    RoundPush,
    ServerPush,
    ShowPush,
    StatusPush,
    StoryAskingPush,
    StoryPush,
)
from claude_review.presentation.schemas.threads import anchor_from_domain
from claude_review.presentation.version_labels import changes_since_round


def push_of(event: PageEvent) -> ServerPush:
    """The push a page reads for what happened."""
    match event:
        case ThreadAnswered():
            return ReplyPush(thread_id=event.thread_id, question_id=event.question_id, body=event.body)
        case ThreadHandedOver():
            return HandedPush(thread_id=event.thread_id, said=event.said)
        case AnswererChanged():
            return AnswererPush(attached=event.attached)
        case AgentSaid():
            return ChatPush(said_id=event.said_id, message_id=event.message_id, body=event.body, files=event.files)
        case WorkReported():
            return ProgressPush(work=made_or_none(AgentWork.from_domain, event.work))
        case FileShown():
            return ShowPush(file=event.file)
        case StatusReported():
            return StatusPush(agent=AgentStatus.from_domain(event.agent))
        case ThreadRaised():
            return PointPush(
                thread_id=event.thread_id,
                anchor=anchor_from_domain(event.anchor),
                body=event.body,
                severity=event.severity,
            )
        case TreeMoved():
            return ChangedPush(moved_count=event.moved_count)
        case RoundBegan():
            return RoundPush(number=event.number)
        case DiffRetaken():
            return DiffPush(file_count=event.file_count, changes=made_or_none(changes_since_round, event.changes))
        case StoryTold():
            return StoryPush()
        case StoryAskingChanged():
            return StoryAskingPush(asking=made_or_none(StoryAsking.from_domain, event.asking))
        case ReviewEnded():
            return EndedPush(finished=event.finished)
        case _:
            assert_never(event)

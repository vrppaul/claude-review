"""What a page reads for each thing that happens in the review: one push per page event.

The review says what happened in its own words, as a domain event; the page
reads it as a push of the wire. This is the one place each event becomes
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
    StoryTold,
    ThreadAnswered,
    ThreadRaised,
    TreeMoved,
    WorkReported,
)
from claude_review.presentation.version_words import changes_on_the_wire
from claude_review.presentation.wire.agent import AgentStatus, AgentWork
from claude_review.presentation.wire.pushes import (
    AnswererPush,
    ChangedPush,
    ChatPush,
    DiffPush,
    EndedPush,
    PointPush,
    ProgressPush,
    ReplyPush,
    RoundPush,
    ServerPush,
    ShowPush,
    StatusPush,
    StoryPush,
)
from claude_review.presentation.wire.threads import anchor_on_the_wire


def push_of(event: PageEvent) -> ServerPush:
    """The push a page reads for what happened."""
    match event:
        case ThreadAnswered():
            return ReplyPush(thread_id=event.thread_id, question_id=event.question_id, body=event.body)
        case AnswererChanged():
            return AnswererPush(attached=event.attached)
        case AgentSaid():
            return ChatPush(said_id=event.said_id, message_id=event.message_id, body=event.body, files=event.files)
        case WorkReported():
            return ProgressPush(work=AgentWork.of(event.work) if event.work is not None else None)
        case FileShown():
            return ShowPush(file=event.file)
        case StatusReported():
            return StatusPush(agent=AgentStatus.of(event.agent))
        case ThreadRaised():
            return PointPush(
                thread_id=event.thread_id,
                anchor=anchor_on_the_wire(event.anchor),
                body=event.body,
                severity=event.severity,
            )
        case TreeMoved():
            return ChangedPush(moved_count=event.moved_count)
        case RoundBegan():
            return RoundPush(number=event.number)
        case DiffRetaken():
            return DiffPush(file_count=event.file_count, changes=changes_on_the_wire(event.changes))
        case StoryTold():
            return StoryPush(round=event.round)
        case ReviewEnded():
            return EndedPush(finished=event.finished)
        case _:
            assert_never(event)

"""Telling every page open on the review what happened, down its session socket.

Each event is written as the push the page reads once, as it stands the
moment it is told, and every page is sent those same words: nothing that
changes afterwards — the work reported again, a status replaced — reaches a
push still waiting to be sent.

A page holds only so much unsent. One that falls further behind than that is
not reading — a frozen tab, a network gone — and is let go rather than held
in memory without end: its socket closes, and a page that is still there
reconnects and reads the review afresh.
"""

import asyncio
from typing import assert_never

import structlog

from claude_review.domain.page_events import (
    AgentSaid,
    AnswererChanged,
    DiffRetaken,
    FileShown,
    PageEvent,
    RoundBegan,
    StatusReported,
    ThreadAnswered,
    ThreadRaised,
    TreeMoved,
    WorkReported,
)
from claude_review.presentation.schemas import (
    AnswererPush,
    ChangedPush,
    ChatPush,
    DiffPush,
    PointPush,
    ProgressPush,
    ReplyPush,
    RoundPush,
    ServerPush,
    ShowPush,
    StatusPush,
)

log = structlog.get_logger()

# How many pushes one page may have waiting before it counts as gone. Far more
# than a review says in a burst: a round, its answers and the work around them.
PAGE_BACKLOG = 256


class BrowserBroadcast:
    """The pages listening to the review, each with the pushes not yet sent to it."""

    def __init__(self, backlog: int) -> None:
        self._backlog = backlog
        self._listeners: set[asyncio.Queue[str]] = set()

    def tell(self, event: PageEvent) -> None:
        """Tell every page open now, in the words of its push, written once."""
        said = push_of(event).model_dump_json()
        for queue in list(self._listeners):
            try:
                queue.put_nowait(said)
            except asyncio.QueueFull:
                self._let_go(queue)

    def listen(self, first: list[PageEvent]) -> asyncio.Queue[str]:
        """Take a page's socket on as a listener, starting with what it must be told before anything new.

        The queue is shut down once the page falls too far behind; reading it
        then raises `asyncio.QueueShutDown`.
        """
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=self._backlog)
        for event in first:
            queue.put_nowait(push_of(event).model_dump_json())
        self._listeners.add(queue)
        return queue

    def stop_listening(self, queue: asyncio.Queue[str]) -> None:
        self._listeners.discard(queue)

    def _let_go(self, queue: asyncio.Queue[str]) -> None:
        """Stop telling a page that is not reading, and drop what it never read."""
        self._listeners.discard(queue)
        queue.shutdown(immediate=True)
        log.warning("page_fell_behind", backlog=self._backlog)


def push_of(event: PageEvent) -> ServerPush:
    """The push a page reads for what happened."""
    match event:
        case ThreadAnswered():
            return ReplyPush(thread_id=event.thread_id, question_id=event.question_id, body=event.body)
        case AnswererChanged():
            return AnswererPush(attached=event.attached)
        case AgentSaid():
            return ChatPush(message_id=event.message_id, body=event.body, files=event.files)
        case WorkReported():
            return ProgressPush(work=event.work)
        case FileShown():
            return ShowPush(file=event.file)
        case StatusReported():
            return StatusPush(agent=event.agent)
        case ThreadRaised():
            return PointPush(thread_id=event.thread_id, anchor=event.anchor, body=event.body, severity=event.severity)
        case TreeMoved():
            return ChangedPush(moved_count=event.moved_count)
        case RoundBegan():
            return RoundPush(number=event.number)
        case DiffRetaken():
            return DiffPush(changes=event.changes)
        case _:
            assert_never(event)

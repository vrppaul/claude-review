"""Telling every page open on the review what happened, down its session socket.

Each event is written as the push the page reads once, as it stands the
moment it is told, and every page is sent those same words: nothing that
changes afterwards — the work reported again, a status replaced — reaches a
push still waiting to be sent.

Every push is numbered across the run of the review, and the last few are
kept. A page whose socket dropped — a laptop asleep, a network gone —
comes back with the number it last had and is handed what it missed. One
gone longer than is kept, or coming back to another run of the review, is
told it was not, and reads the review's facts again instead.

A page holds only so much unsent. One that falls further behind than that is
not reading — a frozen tab, a network gone — and is let go rather than held
in memory without end: its socket closes, and a page that is still there
comes back as any other does.
"""

import asyncio
import secrets
from collections import deque
from typing import assert_never, override

import structlog
from pydantic import BaseModel, ConfigDict

from claude_review.domain.interfaces import PageChannel
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
from claude_review.presentation.version_words import changes_on_the_wire
from claude_review.presentation.wire.agent import AgentStatus, AgentWork
from claude_review.presentation.wire.pushes import (
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
from claude_review.presentation.wire.session import Delivery, Resume, Welcome
from claude_review.presentation.wire.threads import anchor_on_the_wire

log = structlog.get_logger()

# How many pushes one page may have waiting before it counts as gone. Far more
# than a review says in a burst: a round, its answers and the work around them.
PAGE_BACKLOG = 256
# How many backlogs' worth of pushes the review keeps for pages coming back.
# More than one: a page let go for falling a backlog behind must still find
# what it missed, with room for what was said while it reconnected.
JOURNAL_DEPTH = 2
# How many random bytes name one run of the review
RUN_NAME_BYTES = 8
# The welcome that opens every connection takes a place of its own
WELCOME_PLACES = 1


class TellingPosition(BaseModel):
    """How far the review's telling has got: which run of the review, and the number of the last push told."""

    model_config = ConfigDict(frozen=True)

    instance: str
    sequence: int


class Told(BaseModel):
    """One push as it was told, with its number."""

    model_config = ConfigDict(frozen=True)

    sequence: int
    said: str


class BrowserBroadcast(PageChannel):
    """The pages listening to the review, each with the pushes not yet sent to it, and the last pushes told."""

    def __init__(self, backlog: int) -> None:
        self._backlog = backlog
        self._listeners: set[asyncio.Queue[str]] = set()
        # Which run of the review this is: a review restarted on the same
        # port numbers its pushes afresh, and a page must not mistake one
        # run's numbers for the other's
        self._instance = secrets.token_hex(RUN_NAME_BYTES)
        self._journal: deque[Told] = deque(maxlen=backlog * JOURNAL_DEPTH)
        self._sequence = 0

    @override
    def tell(self, event: PageEvent) -> None:
        """Tell every page open now, in the words of its push, written once and numbered."""
        self._sequence += 1
        said = Delivery(sequence=self._sequence, push=push_of(event)).model_dump_json()
        self._journal.append(Told(sequence=self._sequence, said=said))
        for queue in list(self._listeners):
            try:
                queue.put_nowait(said)
            except asyncio.QueueFull:
                self._let_go(queue)

    def listen(self, resume: Resume | None) -> asyncio.Queue[str]:
        """Take a page's socket on as a listener: welcomed, and handed what it missed if it is coming back.

        The queue is shut down once the page falls too far behind; reading it
        then raises `asyncio.QueueShutDown`.
        """
        missed = self._missed_since(resume)
        handed = missed or []
        # What it missed waits already; a backlog on top of it is what it may fall behind by
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=self._backlog + WELCOME_PLACES + len(handed))
        welcome = Welcome(instance=self._instance, sequence=self._sequence, resumed=missed is not None)
        queue.put_nowait(welcome.model_dump_json())
        for told in handed:
            queue.put_nowait(told.said)
        self._listeners.add(queue)
        return queue

    def stop_listening(self, queue: asyncio.Queue[str]) -> None:
        self._listeners.discard(queue)

    def position(self) -> TellingPosition:
        """How far the telling has got: where a page reading the review's facts now goes on from."""
        return TellingPosition(instance=self._instance, sequence=self._sequence)

    def _missed_since(self, resume: Resume | None) -> list[Told] | None:
        """What a page coming back missed, or None when it cannot be handed all of it."""
        if resume is None or resume.instance != self._instance or resume.after > self._sequence:
            return None
        oldest_kept = self._journal[0].sequence if self._journal else self._sequence + 1
        if resume.after + 1 < oldest_kept:
            return None
        return [told for told in self._journal if told.sequence > resume.after]

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
        case _:
            assert_never(event)

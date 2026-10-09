"""What the reader has handed over for the agent, kept until the agent takes it."""

import asyncio
from collections import deque
from collections.abc import Awaitable
from enum import StrEnum, auto

from claude_review.domain.models import AgentEvent
from claude_review.services.review_lifetime import ReviewLifetime


class Silence(StrEnum):
    """Why a wait for the next event ended with nothing taken.

    TIMED_OUT — nothing arrived in the time the caller gave it.
    CLOSED — the review is over, and nothing handed over is left.
    CALLER_LEFT — whoever was waiting went away; what arrives next is kept
    for whoever asks next.
    """

    TIMED_OUT = auto()
    CLOSED = auto()
    CALLER_LEFT = auto()


class AgentInbox:
    """Questions, rounds and panel messages, in the order the reader handed them over.

    One queue rather than several, so they are answered in the order they
    were sent — an answer written after a round must not arrive before it. A
    queue rather than a callback: asking and answering are separate
    processes, and the agent takes one thing at a time, in a loop of polls
    that each may be killed or time out.

    Two rules keep anything from being lost between those polls. What was
    handed over outranks the review ending: a round sent as the last act is
    read before the agent hears the review is over. And a poll whose caller
    went away takes nothing: a server does not stop a handler whose client
    left, and one left waiting would swallow the next question for nobody.
    A caller leaving in the very instant its event is handed out still loses
    it; only an acknowledgement could close that, and the loop has none.
    """

    def __init__(self, lifetime: ReviewLifetime) -> None:
        self._lifetime = lifetime
        self._waiting: deque[AgentEvent] = deque()
        # Set while anything waits to be taken, so a poll can sleep until it does
        self._filled = asyncio.Event()

    def hand_in(self, event: AgentEvent) -> None:
        """Keep something the reader handed over, behind whatever came before it."""
        self._waiting.append(event)
        self._filled.set()

    async def take(self, *, within: float, caller_left: Awaitable[None]) -> AgentEvent | Silence:
        """The next thing handed over, or why there is none.

        Waits up to `within` seconds for something to arrive, and no longer
        than whoever asked is there: `caller_left` finishes when they go.
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + within
        leaving = asyncio.ensure_future(caller_left)
        closing = asyncio.ensure_future(self._lifetime.until_ended())
        try:
            while True:
                if leaving.done():
                    return Silence.CALLER_LEFT
                if self._waiting:
                    return self._next()
                if closing.done():
                    return Silence.CLOSED
                remaining = deadline - loop.time()
                if remaining <= 0:
                    return Silence.TIMED_OUT
                await self._until_something_changes(remaining, leaving, closing)
        finally:
            leaving.cancel()
            closing.cancel()

    def drain(self) -> list[AgentEvent]:
        """Take everything nobody took, in the order it was handed over: the review is over."""
        left = list(self._waiting)
        self._waiting.clear()
        self._filled.clear()
        return left

    def _next(self) -> AgentEvent:
        event = self._waiting.popleft()
        if not self._waiting:
            self._filled.clear()
        return event

    async def _until_something_changes(self, seconds: float, *watched: asyncio.Future[None]) -> None:
        """Sleep until something arrives, one of the watched finishes, or time is up.

        Two polls may wake for one arrival; the one that finds it gone goes
        back to sleep.
        """
        filling = asyncio.ensure_future(self._filled.wait())
        try:
            await asyncio.wait({filling, *watched}, timeout=seconds, return_when=asyncio.FIRST_COMPLETED)
        finally:
            filling.cancel()

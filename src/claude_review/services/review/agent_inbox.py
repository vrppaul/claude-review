"""What the reader has handed over for the agent, kept until the agent takes it."""

import asyncio
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Awaitable
from enum import StrEnum, auto

from claude_review.domain.models import AgentEvent, SaidToTheAgent
from claude_review.services.review.review_lifetime import ReviewLifetime


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


class StandingRequest(ABC):
    """Something an agent is to be handed that nobody said: a state the review keeps, due while it lasts.

    A story being wanted is one. Kept by its owner rather than copied into
    the inbox, it cannot be wanted in one place and not in the other; the
    inbox only hands it out, once whatever someone said has been taken.
    """

    @property
    @abstractmethod
    def due(self) -> asyncio.Event:
        """Set while the request waits for an agent to take it."""

    @abstractmethod
    def claim(self) -> AgentEvent | None:
        """The request, noted as taken by whoever is handed it, with no await between: None where it is not due."""


class AgentInbox:
    """Questions, rounds, panel messages and stops, in the order the reader handed them over, then what stands.

    One queue rather than several, so they are answered in the order they
    were sent — an answer written after a round must not arrive before it. A
    queue rather than a callback: asking and answering are separate
    processes, and the agent takes one thing at a time, in a loop of polls
    that each may be killed or time out. What the review wants of the agent
    without anyone saying it, a standing request, is handed out when nothing
    said waits: the reader's own words come first, and a story asked for is
    then told of the code the rounds before it left.

    Two rules keep anything from being lost between those polls. What was
    handed over outranks the review ending: a round sent as the last act is
    read before the agent hears the review is over. And a poll whose caller
    went away takes nothing: a server does not stop a handler whose client
    left, and one left waiting would swallow the next question for nobody.
    A caller leaving in the very instant its event is handed out still loses
    it; only an acknowledgement could close that, and the loop has none.

    What nobody has taken can be taken back (`withdraw`), and is then
    handed to no agent. The inbox alone knows whether anybody took it, so
    it is the one to say.
    """

    def __init__(self, lifetime: ReviewLifetime, standing: StandingRequest) -> None:
        self._lifetime = lifetime
        self._standing = standing
        self._waiting: deque[SaidToTheAgent] = deque()
        # Set while anything waits to be taken, so a poll can sleep until it does
        self._filled = asyncio.Event()

    def hand_in(self, event: SaidToTheAgent) -> None:
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
                # Asked of the review itself: the watch on its end hears of it a turn of the loop later
                if self._lifetime.has_ended:
                    return Silence.CLOSED
                claimed = self._standing.claim()
                if claimed is not None:
                    return claimed
                remaining = deadline - loop.time()
                if remaining <= 0:
                    return Silence.TIMED_OUT
                await self._until_something_changes(remaining, leaving, closing)
        finally:
            leaving.cancel()
            closing.cancel()

    def withdraw(self, event: SaidToTheAgent) -> bool:
        """Take back something handed over, while nobody has taken it, and say whether it was still waiting.

        Once an agent has it, it cannot be taken back: whoever asks is told
        so, and tells the agent another way.
        """
        if event not in self._waiting:
            return False
        self._waiting.remove(event)
        self._sleep_once_emptied()
        return True

    def drain(self) -> list[SaidToTheAgent]:
        """Take everything nobody took, in the order it was handed over: the review is over."""
        left = list(self._waiting)
        self._waiting.clear()
        self._sleep_once_emptied()
        return left

    def _next(self) -> SaidToTheAgent:
        event = self._waiting.popleft()
        self._sleep_once_emptied()
        return event

    def _sleep_once_emptied(self) -> None:
        """Let a poll sleep again once nothing waits to be taken."""
        if not self._waiting:
            self._filled.clear()

    async def _until_something_changes(self, seconds: float, *watched: asyncio.Future[None]) -> None:
        """Sleep until something arrives, a standing request falls due, one of the watched finishes, or time is up.

        Two polls may wake for one arrival; the one that finds it gone goes
        back to sleep.
        """
        filling = asyncio.ensure_future(self._filled.wait())
        falling_due = asyncio.ensure_future(self._standing.due.wait())
        try:
            await asyncio.wait({filling, falling_due, *watched}, timeout=seconds, return_when=asyncio.FIRST_COMPLETED)
        finally:
            filling.cancel()
            falling_due.cancel()

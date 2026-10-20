"""When a review ends, and why.

A review ends in several ways: the reader sends it for good, closes its tab
or never opens it, the process is stopped, or its server stops on its own.
Whichever comes first ends it for everyone at once — the server, the agent
waiting on it, the watcher of the tree, the pages still open on it — and the
reason is said once, by that first one.
"""

import asyncio
import contextlib
from collections.abc import Awaitable
from enum import StrEnum, auto

import structlog

from claude_review.domain.interfaces import PageChannel
from claude_review.domain.page_events import ReviewEnded

log = structlog.get_logger()


class EndReason(StrEnum):
    """Why a review ended.

    FINISHED — the reader sent it and ended it.
    BROWSER_CLOSED — its page was closed and not opened again in time.
    NEVER_OPENED — no page opened it in the time it waits for one.
    STOPPED — the process was stopped: Ctrl+C, or `kill`.
    SERVER_STOPPED — its server stopped on its own, or never came up.
    FAULT — something the review cannot run without failed.
    """

    FINISHED = auto()
    BROWSER_CLOSED = auto()
    NEVER_OPENED = auto()
    STOPPED = auto()
    SERVER_STOPPED = auto()
    FAULT = auto()


class ReviewLifetime:
    """Whether a review is still running, and why it ended once it has."""

    def __init__(self, page: PageChannel) -> None:
        # Where the pages open on the review are told it is over, the moment it is
        self._page = page
        self._ended = asyncio.Event()
        self._reason: EndReason | None = None

    @property
    def has_ended(self) -> bool:
        return self._ended.is_set()

    @property
    def reason(self) -> EndReason | None:
        """Why it ended, once it has."""
        return self._reason

    def end(self, reason: EndReason) -> None:
        """End the review, unless something has already: the first reason is the one kept.

        The pages are told before anything waiting on the end hears of it, so
        the server stopping cannot close their sockets ahead of the news: a
        page never told keeps trying to reach a review that is gone.
        """
        if self.has_ended:
            return
        self._reason = reason
        log.info("review_ended", reason=reason)
        self._page.tell(ReviewEnded(finished=reason is EndReason.FINISHED))
        self._ended.set()

    async def until_ended(self) -> None:
        """Return once the review has ended."""
        await self._ended.wait()

    async def before_the_end(self, awaited: Awaitable[object]) -> bool:
        """Wait for `awaited` or for the review to end, and say whether `awaited` finished first.

        Whatever is still waiting once the review is over is called off, so
        nothing a review runs outlives it.
        """
        waiting = asyncio.ensure_future(awaited)
        ending = asyncio.ensure_future(self._ended.wait())
        try:
            await asyncio.wait({waiting, ending}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            waiting.cancel()
            ending.cancel()
        if waiting.cancelled() or not waiting.done():
            return False
        # Raises whatever it failed with: a failure is not the review ending
        waiting.result()
        return True

    async def ended_within(self, seconds: float) -> bool:
        """Wait up to `seconds` for the review to end, and say whether it has."""
        with contextlib.suppress(TimeoutError):
            async with asyncio.timeout(seconds):
                await self._ended.wait()
        return self.has_ended

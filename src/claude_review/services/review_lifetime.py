"""When a review ends, and why.

A review ends in several ways: the reader sends it for good, closes its tab,
the process is stopped, or its server stops on its own. Whichever comes
first ends it for everyone at once — the server, the agent waiting on it,
the watcher of the tree — and the reason is said once, by that first one.
"""

import asyncio
import contextlib
from enum import StrEnum, auto

import structlog

log = structlog.get_logger()


class EndReason(StrEnum):
    """Why a review ended.

    FINISHED — the reader sent it and ended it.
    BROWSER_CLOSED — its page was closed and not opened again in time.
    STOPPED — the process was stopped: Ctrl+C, or `kill`.
    SERVER_STOPPED — its server stopped on its own, or never came up.
    """

    FINISHED = auto()
    BROWSER_CLOSED = auto()
    STOPPED = auto()
    SERVER_STOPPED = auto()


class ReviewLifetime:
    """Whether a review is still running, and why it ended once it has."""

    def __init__(self) -> None:
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
        """End the review, unless something has already: the first reason is the one kept."""
        if self.has_ended:
            return
        self._reason = reason
        log.info("review_ended", reason=reason)
        self._ended.set()

    async def until_ended(self) -> None:
        """Return once the review has ended."""
        await self._ended.wait()

    async def ended_within(self, seconds: float) -> bool:
        """Wait up to `seconds` for the review to end, and say whether it has."""
        with contextlib.suppress(TimeoutError):
            async with asyncio.timeout(seconds):
                await self._ended.wait()
        return self.has_ended

"""Whether the review is on the reader's screen: its pages, open and closed.

The page holds a socket open for as long as the review is on screen, which
is how the review knows it is still being read. A poll could not tell: a
background tab has its timers throttled to about once a minute, and a
review left open in another tab would look abandoned. A socket is not
throttled.

Nothing here looks at a clock. A page opening or closing is what moves it,
and a closed page is given a moment to come back before the reader counts
as gone. A review no page has opened is given a while for its first: one
started in the background and never opened would otherwise hold its port
and its memory until the machine stops.
"""

import asyncio
import contextlib
from collections.abc import Generator

from claude_review.services.review.review_lifetime import EndReason

# How long the review may have no page open before the reader counts as gone.
# A reload drops the socket and takes it again within a moment.
RELOAD_GRACE_SECONDS = 3.0
# How long a review waits for its first page before it takes it that nobody is
# coming: an hour. Long, since ending too soon costs the reader a review started
# again, at the same address, and waiting on costs a port and some memory.
FIRST_PAGE_DEADLINE_SECONDS = 3600.0


class BrowserPresence:
    """The pages a review has open, and when its reader is gone: the last page closed for good, or none came in time."""

    def __init__(self, reload_grace: float, first_page_deadline: float) -> None:
        self._reload_grace = reload_grace
        self._first_page_deadline = first_page_deadline
        self._open_pages = 0
        # Set while at least one page is open
        self._shown = asyncio.Event()
        # Set once any page has opened: before that, no page is not news
        self._ever_shown = asyncio.Event()
        # Set while no page is open, once one has been
        self._alone = asyncio.Event()

    @contextlib.contextmanager
    def page_open(self) -> Generator[None]:
        """Count a page as open for as long as this lasts: every page that opens also closes."""
        self._open_pages += 1
        self._shown.set()
        self._ever_shown.set()
        self._alone.clear()
        try:
            yield
        finally:
            self._open_pages -= 1
            if self._open_pages == 0:
                self._shown.clear()
                self._alone.set()

    async def until_first_page(self) -> None:
        """Return once a page has opened the review."""
        await self._ever_shown.wait()

    async def until_gone(self) -> EndReason:
        """Return once the reader is gone, and say how.

        Every page has closed and none came back within the grace period, or
        no page opened within the deadline. Until then a review nobody has
        opened yet waits: starting without a page is how every review starts.
        """
        try:
            async with asyncio.timeout(self._first_page_deadline):
                await self._ever_shown.wait()
        except TimeoutError:
            return EndReason.NEVER_OPENED
        while True:
            await self._alone.wait()
            try:
                async with asyncio.timeout(self._reload_grace):
                    await self._shown.wait()
            except TimeoutError:
                return EndReason.BROWSER_CLOSED

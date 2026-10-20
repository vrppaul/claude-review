"""When the reader counts as gone: their page closed, rather than reloaded or not yet opened.

Only the running review acts on this, by ending — which test_cli_process
watches against the real grace period, and test_serving against a short wait
for a first page that never comes. Here the grace is a moment long, so what
it decides can be said without waiting it out.
"""

import asyncio

from claude_review.services.review.browser_presence import FIRST_PAGE_DEADLINE_SECONDS, BrowserPresence
from claude_review.services.review.review_lifetime import EndReason
from tests.helpers import SETTLE_SECONDS

# A grace period short enough for a test to outlast it several times over
GRACE_SECONDS = 0.05
# Long enough for a grace period to have run out had nothing come back within it
OUTLAST_SECONDS = GRACE_SECONDS * 4


def _presence() -> BrowserPresence:
    """The reader's presence with a moment's grace, and the real wait for a first page, which no test outlasts."""
    return BrowserPresence(reload_grace=GRACE_SECONDS, first_page_deadline=FIRST_PAGE_DEADLINE_SECONDS)


async def _still_open_after(watched: asyncio.Future[EndReason]) -> bool:
    """Whether the reader still counts as there once the grace period has had time to run out."""
    done, _ = await asyncio.wait({watched}, timeout=OUTLAST_SECONDS)
    watched.cancel()
    return not done


async def test_a_closed_page_that_does_not_come_back_is_the_reader_leaving() -> None:
    presence = _presence()
    with presence.page_open():
        gone = asyncio.ensure_future(presence.until_gone())

    assert await asyncio.wait_for(gone, timeout=SETTLE_SECONDS) == EndReason.BROWSER_CLOSED


async def test_a_reload_is_not_the_reader_leaving() -> None:
    """A reload drops the socket and takes it again within a moment."""
    presence = _presence()
    with presence.page_open():
        gone = asyncio.ensure_future(presence.until_gone())
    # A turn of the loop: the watch sees the page closed before it comes back
    await asyncio.sleep(0)
    with presence.page_open():
        assert await _still_open_after(gone)


async def test_a_review_nobody_has_opened_yet_keeps_waiting() -> None:
    """Starting without a page is normal; it is not an abandoned review."""
    presence = _presence()

    assert await _still_open_after(asyncio.ensure_future(presence.until_gone()))


async def test_a_page_open_past_the_wait_for_the_first_keeps_the_review_open() -> None:
    """The wait is for a first page alone: once one has come, the review lives as long as a page holds it."""
    presence = BrowserPresence(reload_grace=GRACE_SECONDS, first_page_deadline=GRACE_SECONDS)
    with presence.page_open():
        assert await _still_open_after(asyncio.ensure_future(presence.until_gone()))


async def test_a_second_tab_keeps_the_review_open() -> None:
    presence = _presence()
    with presence.page_open():
        gone = asyncio.ensure_future(presence.until_gone())
        with presence.page_open():
            pass

        assert await _still_open_after(gone)


async def test_the_first_page_to_open_is_heard() -> None:
    """What has to wait for a reader — the watch on the tree — waits for this rather than looking early."""
    presence = _presence()
    opened = asyncio.ensure_future(presence.until_first_page())

    with presence.page_open():
        await asyncio.wait_for(opened, timeout=SETTLE_SECONDS)

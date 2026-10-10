"""Whether anything is there to answer the review, as the review hears it.

The agent lives in another process and is known only by asking: a lease it
renews each time it calls, held for as long as it waits on the review, and
lapsing once it has gone quiet. Rounds are offered only while it is held.
Here the lease is a moment long, so a lapse can be watched happen.
"""

import asyncio
from typing import override

from claude_review.domain.interfaces import PageChannel
from claude_review.domain.page_events import AnswererChanged, PageEvent
from claude_review.services.review.answerer import Answerer
from tests.helpers import FixedClock

# A lease short enough for a test to outlast it several times over
LEASE_SECONDS = 0.05
# Long enough for the lease to have lapsed had nothing renewed it
OUTLAST_SECONDS = LEASE_SECONDS * 4
# When anything the agent says is dated, here
A_MOMENT = 1_791_000_000_000


class RecordingPage(PageChannel):
    """Pages on screen, as a test: what they are told, in order."""

    def __init__(self) -> None:
        self.told: list[PageEvent] = []

    @override
    def tell(self, event: PageEvent) -> None:
        self.told.append(event)


def _answerer(page: RecordingPage) -> Answerer:
    return Answerer(page, FixedClock(A_MOMENT), lease_seconds=LEASE_SECONDS)


async def test_an_agent_heard_is_there_and_the_pages_are_told_once() -> None:
    page = RecordingPage()
    answerer = _answerer(page)

    answerer.heard()
    answerer.heard()

    assert answerer.attached
    assert page.told == [AnswererChanged(attached=True)]


async def test_an_agent_gone_quiet_past_its_lease_is_no_longer_there() -> None:
    """A dead agent must not leave rounds on offer to nobody."""
    page = RecordingPage()
    answerer = _answerer(page)

    answerer.heard()
    await asyncio.sleep(OUTLAST_SECONDS)

    assert not answerer.attached
    assert page.told == [AnswererChanged(attached=True), AnswererChanged(attached=False)]


async def test_an_agent_waiting_on_the_review_is_there_however_long_it_waits() -> None:
    page = RecordingPage()
    answerer = _answerer(page)

    with answerer.waiting():
        await asyncio.sleep(OUTLAST_SECONDS)

        assert answerer.attached


async def test_the_lease_runs_from_the_end_of_the_last_wait() -> None:
    """An agent between two polls is still there: the next poll comes a moment later."""
    page = RecordingPage()
    answerer = _answerer(page)

    with answerer.waiting():
        await asyncio.sleep(OUTLAST_SECONDS)

    assert answerer.attached
    await asyncio.sleep(OUTLAST_SECONDS)
    assert not answerer.attached


async def test_an_agent_that_comes_back_is_there_again() -> None:
    page = RecordingPage()
    answerer = _answerer(page)
    answerer.heard()
    await asyncio.sleep(OUTLAST_SECONDS)

    answerer.heard()

    assert answerer.attached
    assert page.told[-1] == AnswererChanged(attached=True)

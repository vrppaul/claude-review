"""When a review ends, and why: whatever ends it first says so, once."""

import asyncio

from claude_review.services.review_lifetime import EndReason, ReviewLifetime
from tests.helpers import SETTLE_SECONDS

# Long enough to be sure nothing ended the review, short enough to cost nothing
GLANCE_SECONDS = 0.01


def test_a_review_runs_until_something_ends_it() -> None:
    lifetime = ReviewLifetime()

    assert not lifetime.has_ended
    assert lifetime.reason is None


def test_the_first_reason_a_review_ended_for_is_the_one_it_keeps() -> None:
    """A browser closing as the process is killed must not rewrite why it ended."""
    lifetime = ReviewLifetime()

    lifetime.end(EndReason.FINISHED)
    lifetime.end(EndReason.BROWSER_CLOSED)

    assert lifetime.has_ended
    assert lifetime.reason == EndReason.FINISHED


async def test_whoever_waits_on_a_review_hears_it_end() -> None:
    lifetime = ReviewLifetime()
    waiting = asyncio.ensure_future(lifetime.until_ended())

    lifetime.end(EndReason.STOPPED)

    await asyncio.wait_for(waiting, timeout=SETTLE_SECONDS)


async def test_a_look_at_a_review_still_running_says_it_has_not_ended() -> None:
    """What a loop checking on the review sleeps on between looks."""
    lifetime = ReviewLifetime()

    assert not await lifetime.ended_within(GLANCE_SECONDS)

    lifetime.end(EndReason.SERVER_STOPPED)

    assert await lifetime.ended_within(GLANCE_SECONDS)

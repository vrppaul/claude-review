"""When a review ends, and why: whatever ends it first says so, once — to the log and to every page open on it."""

import asyncio

from claude_review.domain.page_events import ReviewEnded
from claude_review.services.review.review_lifetime import EndReason, ReviewLifetime
from tests.helpers import SETTLE_SECONDS, RecordingPage

# Long enough to be sure nothing ended the review, short enough to cost nothing
GLANCE_SECONDS = 0.01


def test_a_review_runs_until_something_ends_it() -> None:
    lifetime = ReviewLifetime(RecordingPage())

    assert not lifetime.has_ended
    assert lifetime.reason is None


def test_the_first_reason_a_review_ended_for_is_the_one_it_keeps() -> None:
    """A browser closing as the process is killed must not rewrite why it ended."""
    lifetime = ReviewLifetime(RecordingPage())

    lifetime.end(EndReason.FINISHED)
    lifetime.end(EndReason.BROWSER_CLOSED)

    assert lifetime.has_ended
    assert lifetime.reason == EndReason.FINISHED


async def test_whoever_waits_on_a_review_hears_it_end() -> None:
    lifetime = ReviewLifetime(RecordingPage())
    waiting = asyncio.ensure_future(lifetime.until_ended())

    lifetime.end(EndReason.STOPPED)

    await asyncio.wait_for(waiting, timeout=SETTLE_SECONDS)


async def test_a_look_at_a_review_still_running_says_it_has_not_ended() -> None:
    """What a loop checking on the review sleeps on between looks."""
    lifetime = ReviewLifetime(RecordingPage())

    assert not await lifetime.ended_within(GLANCE_SECONDS)

    lifetime.end(EndReason.SERVER_STOPPED)

    assert await lifetime.ended_within(GLANCE_SECONDS)


async def test_what_finishes_before_the_review_ends_is_said_to_have_come_first() -> None:
    lifetime = ReviewLifetime(RecordingPage())
    arrived = asyncio.Event()
    arrived.set()

    assert await lifetime.before_the_end(arrived.wait())
    assert not lifetime.has_ended


async def test_a_review_ending_first_stops_the_wait_for_anything_else() -> None:
    """A page that never opens must not keep the review's parts waiting after it is over."""
    lifetime = ReviewLifetime(RecordingPage())
    never = asyncio.Event()
    waiting = asyncio.ensure_future(lifetime.before_the_end(never.wait()))

    lifetime.end(EndReason.FINISHED)

    assert not await asyncio.wait_for(waiting, timeout=SETTLE_SECONDS)


def test_the_pages_hear_once_that_the_review_is_over_and_that_the_reader_finished_it() -> None:
    """Sent for good, or ended once everything had gone: what a page holds of it is done with."""
    page = RecordingPage()
    lifetime = ReviewLifetime(page)

    lifetime.end(EndReason.FINISHED)
    lifetime.end(EndReason.BROWSER_CLOSED)

    assert page.told == [ReviewEnded(finished=True)]


def test_the_pages_hear_that_a_review_stopped_under_the_reader_was_not_finished() -> None:
    """Ctrl+C, its server stopping, a fault: what a page has not sent is still the reader's."""
    page = RecordingPage()

    ReviewLifetime(page).end(EndReason.STOPPED)

    assert page.told == [ReviewEnded(finished=False)]

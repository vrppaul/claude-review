"""What every browser test needs: a page to open a review in, servers for the review, and the loop they share.

Chromium is launched once for the run: starting a browser and closing it
for every test was half of what the browser tests took. `browsers_loop.py`
says what sharing it asks of a test and of a fixture.
"""

import asyncio
from collections.abc import AsyncIterator

import pytest
from playwright.async_api import Browser, Page, async_playwright

from tests.e2e.browsers_loop import BROWSERS_LOOP, in_the_browsers_loop
from tests.helpers import ReviewFactory, ReviewServers, review_servers

# How long a browser test waits for anything on the page before failing
E2E_TIMEOUT_MS = 5_000


def pytest_itemcollected(item: pytest.Item) -> None:
    """Put each test of this directory in the browser's loop.

    The marker goes first: of a test's markers of one name the first is the
    one read, and the plugin has given every async test one that names no loop.
    """
    item.add_marker(pytest.mark.asyncio(loop_scope=BROWSERS_LOOP), append=False)


@in_the_browsers_loop(scope="session")
async def browser() -> AsyncIterator[Browser]:
    """The run's one Chromium."""
    async with async_playwright() as playwright:
        launched = await playwright.chromium.launch()
        yield launched
        await launched.close()


@in_the_browsers_loop(autouse=True)
async def nothing_left_running() -> AsyncIterator[None]:
    """Hold a browser test to ending what it started: whatever it left running would run on beside the next test."""
    running_before = asyncio.all_tasks()
    yield
    left_running = asyncio.all_tasks() - running_before - {asyncio.current_task()}
    assert not left_running, f"left running in the loop the browser tests share: {left_running}"


@in_the_browsers_loop
async def page(browser: Browser) -> AsyncIterator[Page]:
    """A fresh page with the suite's timeout, in a context of its own: no test sees another's storage."""
    context = await browser.new_context()
    opened = await context.new_page()
    opened.set_default_timeout(E2E_TIMEOUT_MS)
    yield opened
    await context.close()


@in_the_browsers_loop
async def servers(reviews: ReviewFactory) -> AsyncIterator[ReviewServers]:
    """The suite's `servers` in the browser's loop: a review is served from the loop its page is opened in.

    A fixture that starts a review here is declared with `in_the_browsers_loop`:
    one in a loop of its own is refused by `start`.
    """
    async with review_servers(reviews) as started:
        yield started

"""What every browser test needs: a review served on a real port, and a page to open it in."""

from collections.abc import AsyncIterator

import pytest
from playwright.async_api import Page, async_playwright

from tests.helpers import ReviewFactory, ReviewServers

# How long a browser test waits for anything on the page before failing
E2E_TIMEOUT_MS = 5_000


@pytest.fixture
async def servers(reviews: ReviewFactory) -> AsyncIterator[ReviewServers]:
    """Starts reviews for the test to open, and stops every one of them after it."""
    started = ReviewServers(reviews)
    yield started
    await started.stop()


@pytest.fixture
async def page() -> AsyncIterator[Page]:
    """A fresh browser page with the suite's timeout."""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        context = await browser.new_context()
        opened = await context.new_page()
        opened.set_default_timeout(E2E_TIMEOUT_MS)
        yield opened
        await browser.close()

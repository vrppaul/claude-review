"""What every browser test needs: a page to open a review in."""

from collections.abc import AsyncIterator

import pytest
from playwright.async_api import Page, async_playwright

# How long a browser test waits for anything on the page before failing
E2E_TIMEOUT_MS = 5_000


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

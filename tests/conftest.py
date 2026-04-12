"""Shared fixtures for tests."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from playwright.async_api import Page, async_playwright

from tests.helpers import git

E2E_TIMEOUT_MS = 5_000


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with an initial commit."""
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "test@test.com")
    git(tmp_path, "config", "user.name", "Test")

    (tmp_path / "initial.txt").write_text("initial content\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "initial")

    return tmp_path


@pytest.fixture
async def page() -> AsyncGenerator[Page]:
    """Async Playwright page with centralized timeout."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        pg = await browser.new_page()
        pg.set_default_timeout(E2E_TIMEOUT_MS)
        yield pg
        await browser.close()

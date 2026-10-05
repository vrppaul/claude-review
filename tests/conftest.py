"""Shared fixtures for tests."""

from collections.abc import AsyncGenerator
from importlib.metadata import version
from pathlib import Path

import pytest
from playwright.async_api import Page, async_playwright

from claude_review.domain.models import ReviewWorkspace
from tests.helpers import git

E2E_TIMEOUT_MS = 5_000
# The cookie that says which release a reader has already been shown around
SEEN_RELEASE_COOKIE = "claude-review-seen"


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
def workspace(tmp_path_factory: pytest.TempPathFactory) -> ReviewWorkspace:
    """The directory a review owns, laid out as for one that leaves no marks."""
    return ReviewWorkspace(objects=None, images=tmp_path_factory.mktemp("images"))


@pytest.fixture
def marking_workspace(tmp_path_factory: pytest.TempPathFactory) -> ReviewWorkspace:
    """The directory a review of a repository owns, with room for its marks."""
    return ReviewWorkspace(objects=tmp_path_factory.mktemp("objects"), images=tmp_path_factory.mktemp("images"))


@pytest.fixture
async def page() -> AsyncGenerator[Page]:
    """Async Playwright page with centralized timeout."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        # A reader who has seen this release, so no welcome or news card sits
        # over what a test clicks; the test of the welcome takes it away
        await context.add_cookies(
            [{"name": SEEN_RELEASE_COOKIE, "value": version("claude-review"), "url": "http://127.0.0.1"}]
        )
        pg = await context.new_page()
        pg.set_default_timeout(E2E_TIMEOUT_MS)
        yield pg
        await browser.close()

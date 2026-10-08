"""Shared fixtures for tests."""

from collections.abc import AsyncGenerator
from importlib.metadata import version
from pathlib import Path

import pytest
from playwright.async_api import Page, async_playwright

from claude_review.domain.models import GuideState, ReaderFiles, ReviewWorkspace
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
def workspace(tmp_path_factory: pytest.TempPathFactory) -> ReviewWorkspace:
    """The directory a review owns, laid out as for one that leaves no marks."""
    return ReviewWorkspace(objects=None, images=tmp_path_factory.mktemp("images"))


@pytest.fixture
def marking_workspace(tmp_path_factory: pytest.TempPathFactory) -> ReviewWorkspace:
    """The directory a review of a repository owns, with room for its marks."""
    return ReviewWorkspace(objects=tmp_path_factory.mktemp("objects"), images=tmp_path_factory.mktemp("images"))


@pytest.fixture
def reader_files(tmp_path_factory: pytest.TempPathFactory) -> ReaderFiles:
    """What the reviews remember about their reader, kept apart for each test.

    The reader has seen this release, so no welcome or news card sits over
    what a test clicks; the test of the welcome takes that away.
    """
    directory = tmp_path_factory.mktemp("reader")
    files = ReaderFiles(settings=directory / "settings.json", guide=directory / "guide.json")
    files.guide.write_text(GuideState(seen_release=version("claude-review")).model_dump_json())
    return files


@pytest.fixture
async def page() -> AsyncGenerator[Page]:
    """Async Playwright page with centralized timeout."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        pg = await context.new_page()
        pg.set_default_timeout(E2E_TIMEOUT_MS)
        yield pg
        await browser.close()

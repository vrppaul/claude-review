"""Shared fixtures for tests."""

from collections.abc import AsyncIterator, Iterator
from importlib.metadata import version
from pathlib import Path

import pytest
import structlog
from fastapi.testclient import TestClient
from httpx import AsyncClient
from structlog.testing import capture_logs
from structlog.typing import EventDict

from claude_review.domain.models import GuideState
from claude_review.hosting.workspace import ReaderFiles, ReviewWorkspace
from tests.helpers import ReviewFactory, ReviewServers, git, http_client, one_line_file, opening_of, page_client


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
def reviews(workspace: ReviewWorkspace, marking_workspace: ReviewWorkspace, reader_files: ReaderFiles) -> ReviewFactory:
    """Builds the reviews a test needs, all sharing this test's directories and reader."""
    return ReviewFactory(workspace=workspace, marking_workspace=marking_workspace, reader_files=reader_files)


@pytest.fixture
async def servers(reviews: ReviewFactory) -> AsyncIterator[ReviewServers]:
    """Serves reviews on real ports for the test, and stops every one of them after it."""
    started = ReviewServers(reviews)
    yield started
    await started.stop()


@pytest.fixture
async def client(reviews: ReviewFactory) -> AsyncIterator[AsyncClient]:
    """An agent's way into a review of one file with one line in it."""
    async with http_client(reviews.app(opening_of([one_line_file()]))) as agent:
        yield agent


@pytest.fixture
def review_page(reviews: ReviewFactory) -> Iterator[TestClient]:
    """The review's own page, socket and all, on a review of one file with one line in it."""
    with page_client(reviews.app(opening_of([one_line_file()]))) as page:
        yield page


@pytest.fixture(autouse=True)
def logging_left_as_found() -> Iterator[None]:
    """Put back how logging was set up once a test is over.

    A test that runs the command line sets logging up the way the command
    does, for the whole process — silent short of critical — and no test
    after it should inherit that.
    """
    configured = structlog.get_config()
    yield
    structlog.configure(**configured)


@pytest.fixture
def logged() -> Iterator[list[EventDict]]:
    """What the review logs during a test, at every level, whatever the test sets up."""
    structlog.reset_defaults()
    with capture_logs() as entries:
        yield entries

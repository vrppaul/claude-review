"""Shared fixtures for tests."""

import os
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
from tests.helpers import (
    GIT_YES,
    INITIAL_FILES,
    ReviewFactory,
    ReviewServers,
    committed_repository,
    files_opening_of,
    http_client,
    one_line_file,
    page_client,
    review_servers,
)


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with an initial commit."""
    return committed_repository(tmp_path, INITIAL_FILES)


@pytest.fixture
def workspace(tmp_path_factory: pytest.TempPathFactory) -> ReviewWorkspace:
    """The directory a review owns, laid out as for one that leaves no marks."""
    return ReviewWorkspace(kept=tmp_path_factory.mktemp("kept"), objects=None, images=tmp_path_factory.mktemp("images"))


@pytest.fixture
def marking_workspace(tmp_path_factory: pytest.TempPathFactory) -> ReviewWorkspace:
    """The directory a review of a repository owns, with room for its marks."""
    return ReviewWorkspace(
        kept=tmp_path_factory.mktemp("kept"),
        objects=tmp_path_factory.mktemp("objects"),
        images=tmp_path_factory.mktemp("images"),
    )


@pytest.fixture
def reader_files(tmp_path_factory: pytest.TempPathFactory) -> ReaderFiles:
    """What the reviews remember about their reader, kept apart for each test.

    The reader has seen this release and been introduced to Story, so no
    welcome, news card or introduction at the switch sits over what a test
    clicks; the tests of the welcome and the introduction take that away.
    """
    directory = tmp_path_factory.mktemp("reader")
    files = ReaderFiles(settings=directory / "settings.json", guide=directory / "guide.json")
    files.guide.write_text(GuideState(seen_release=version("claude-review"), story_introduced=True).model_dump_json())
    return files


@pytest.fixture
def reviews(workspace: ReviewWorkspace, marking_workspace: ReviewWorkspace, reader_files: ReaderFiles) -> ReviewFactory:
    """Builds the reviews a test needs, all sharing this test's directories and reader."""
    return ReviewFactory(workspace=workspace, marking_workspace=marking_workspace, reader_files=reader_files)


@pytest.fixture
async def servers(reviews: ReviewFactory) -> AsyncIterator[ReviewServers]:
    """Serves reviews on real ports for the test, and stops every one of them after it."""
    async with review_servers(reviews) as started:
        yield started


@pytest.fixture
async def client(reviews: ReviewFactory) -> AsyncIterator[AsyncClient]:
    """An agent's way into a review of one file with one line in it."""
    async with http_client(reviews.app_of_change([one_line_file()])) as agent:
        yield agent


@pytest.fixture
async def files_client(reviews: ReviewFactory) -> AsyncIterator[AsyncClient]:
    """An agent's way into a review of one file read once: nobody changed it, and nothing takes it again."""
    async with http_client(reviews.app(files_opening_of([one_line_file()]))) as agent:
        yield agent


@pytest.fixture
def review_page(reviews: ReviewFactory) -> Iterator[TestClient]:
    """The review's own page, socket and all, on a review of one file with one line in it."""
    with page_client(reviews.app_of_change([one_line_file()])) as page:
        yield page


# Where git would read settings of the machine's and of whoever runs the
# tests: nowhere, so a developer's own git does not decide what a test reads
NO_GIT_SETTINGS_FILE = "/dev/null"
# What the variables of git's own in the environment are named with
GIT_VARIABLE_PREFIX = "GIT_"


@pytest.fixture(autouse=True)
def git_as_it_comes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every git a test runs with none of the developer's settings or environment.

    Each test repository sets what it needs in its own configuration; what
    a test means to hold the review to, it sets itself.
    """
    inherited = [name for name in os.environ if name.startswith(GIT_VARIABLE_PREFIX)]
    for name in inherited:
        monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", NO_GIT_SETTINGS_FILE)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", GIT_YES)


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

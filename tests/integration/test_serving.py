"""A review held open in this process: what it hands back, whatever else goes wrong while it runs."""

import asyncio
import contextlib
import signal
import tempfile
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path
from typing import override

import pytest
from httpx import URL, AsyncClient
from structlog.typing import EventDict

from claude_review.hosting.announcer import ReviewAnnouncer
from claude_review.hosting.errors import ReviewStoppedError, ServerStartError
from claude_review.hosting.ports import ANY_FREE_PORT
from claude_review.hosting.serving import serve_review, stop_signals
from claude_review.repositories.git_repository import GitRepository, GitStagedTree
from claude_review.services.review.browser_presence import BrowserPresence
from claude_review.services.review.content_sources import RepositorySource
from claude_review.services.review.tree_watcher_service import TreeWatcherService
from claude_review.services.review_opening import ReviewOpening, open_diff
from tests.helpers import SETTLE_SECONDS
from tests.page_socket import page_socket_held

SUBMIT_ROUTE = "/api/submit"
THE_ROUND = "Rename the helper."
# The last round, sent and ending the review
LAST_ROUND = {"threads": [], "body": THE_ROUND, "end": True}
# What the pieces of a staging are called in the temporary directory
STAGING_LEFTOVERS = ("*.git-index", "*.git-objects")


class StagingThatHangs(GitRepository):
    """A repository whose working tree takes git as long as anyone cares to wait to stage, as a huge one does."""

    def __init__(self) -> None:
        super().__init__(objects=None)
        self.staging = asyncio.Event()

    @override
    @contextlib.asynccontextmanager
    async def staged(self, path: Path) -> AsyncGenerator[GitStagedTree]:
        async with super().staged(path) as staged:
            self.staging.set()
            await asyncio.Event().wait()
            yield staged


class RecordingAnnouncer(ReviewAnnouncer):
    """Whoever started the review, as a test: it holds on to what it is told."""

    def __init__(self) -> None:
        self.address: asyncio.Future[str] = asyncio.get_running_loop().create_future()

    @override
    async def listening_at(self, url: str) -> None:
        self.address.set_result(url)

    @override
    def images_left_in(self, directory: Path) -> None:
        """Nothing is pasted in these reviews."""


class FailingWatch:
    """A watch on the tree that fails the first time it looks, as a disk gone away would."""

    def __aiter__(self) -> FailingWatch:
        return self

    async def __anext__(self) -> int:
        failure = "the disk went away"
        raise OSError(failure)


async def _failing_check(*_arguments: object) -> None:
    failure = "the event loop went away"
    raise OSError(failure)


@pytest.fixture(autouse=True)
def kept_under_this_test(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep what the review writes, and what it remembers about its reader, under this test's own directory."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))


@pytest.fixture
def signals_never_end_the_tests() -> Iterator[list[int]]:
    """Catch any stop signal a test sends that nothing of the review answers, rather than let it end the run."""
    unanswered: list[int] = []
    left_as_found = signal.signal(signal.SIGTERM, lambda number, _frame: unanswered.append(number))
    yield unanswered
    signal.signal(signal.SIGTERM, left_as_found)


async def _served(opening: ReviewOpening, announcer: ReviewAnnouncer) -> str:
    """Serve a review the way the command line does, Ctrl+C and `kill` answered from the start."""
    with stop_signals() as signals:
        return await serve_review(opening, port=ANY_FREE_PORT, announcer=announcer, signals=signals)


async def _opened(repo: Path, repository: GitRepository) -> ReviewOpening:
    """Open a review of the repository the way the command line does, Ctrl+C and `kill` answered from the start."""
    with stop_signals():
        return await open_diff(repo, None, repository)


@pytest.fixture
async def opening(tmp_git_repo: Path) -> ReviewOpening:
    (tmp_git_repo / "initial.txt").write_text("changed\n")
    return await open_diff(tmp_git_repo, None, GitRepository(objects=None))


@pytest.fixture
async def announcer() -> RecordingAnnouncer:
    return RecordingAnnouncer()


def _port_of(address: str) -> int:
    """The port the review at this address listens on."""
    port = URL(address).port
    if port is None:
        failure = f"{address} names no port"
        raise AssertionError(failure)
    return port


def _events(logged: list[EventDict]) -> list[str]:
    return [entry["event"] for entry in logged]


async def test_a_watch_on_the_tree_that_fails_leaves_the_review_running_and_its_round_handed_back(
    opening: ReviewOpening, announcer: RecordingAnnouncer, logged: list[EventDict], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The watch only helps; the reader's unsent work and the last round matter more than it."""
    monkeypatch.setattr(TreeWatcherService, "changes", lambda *_arguments, **_keywords: FailingWatch())

    serving = asyncio.ensure_future(_served(opening, announcer))
    address = await asyncio.wait_for(announcer.address, SETTLE_SECONDS)
    # The tree is watched only once a page is there to be told
    async with page_socket_held(_port_of(address)), AsyncClient(base_url=address) as agent:
        await agent.post(SUBMIT_ROUTE, json=LAST_ROUND)

    assert THE_ROUND in await asyncio.wait_for(serving, timeout=SETTLE_SECONDS)
    assert "review_helper_failed" in _events(logged)


async def test_a_review_that_can_no_longer_tell_its_page_closed_ends_rather_than_running_for_good(
    opening: ReviewOpening, announcer: RecordingAnnouncer, logged: list[EventDict], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run on, it would hold its port and keep its agent waiting long after the reader has gone."""
    monkeypatch.setattr(BrowserPresence, "until_closed_for_good", _failing_check)

    handed_back = await asyncio.wait_for(_served(opening, announcer), timeout=SETTLE_SECONDS)

    assert handed_back == ""
    assert "review_part_failed" in _events(logged)


async def _failing_opening(*_arguments: object) -> None:
    failure = "the repository went away"
    raise OSError(failure)


async def test_a_review_that_cannot_open_says_why_and_ends_as_a_fault(
    opening: ReviewOpening, announcer: RecordingAnnouncer, logged: list[EventDict], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Never listening, it must still say what stopped it rather than leave only a server that stopped."""
    monkeypatch.setattr(RepositorySource, "open", _failing_opening)

    with pytest.raises(ServerStartError, match="fault"):
        await asyncio.wait_for(_served(opening, announcer), timeout=SETTLE_SECONDS)

    assert "review_opening_failed" in _events(logged)


async def test_a_stop_signal_while_the_review_opens_leaves_nothing_of_its_staging_behind(
    tmp_git_repo: Path, tmp_path: Path, signals_never_end_the_tests: list[int]
) -> None:
    """`kill` while git stages a large tree: what the staging wrote goes with the review, not left in /tmp."""
    repository = StagingThatHangs()
    opening = asyncio.ensure_future(_opened(tmp_git_repo, repository))
    await asyncio.wait_for(repository.staging.wait(), SETTLE_SECONDS)

    signal.raise_signal(signal.SIGTERM)
    done, _ = await asyncio.wait({opening}, timeout=SETTLE_SECONDS)

    assert opening in done, "the signal stopped nothing"
    with pytest.raises(ReviewStoppedError):
        opening.result()
    assert signals_never_end_the_tests == [], "the signal reached no one who stops the opening"
    assert [left for pattern in STAGING_LEFTOVERS for left in tmp_path.glob(pattern)] == []


async def test_an_opening_cancelled_by_anything_but_a_stop_signal_stays_cancelled(tmp_git_repo: Path) -> None:
    """Only a signal's own stop is said as one: whatever else cancels the work is told it was cancelled."""
    repository = StagingThatHangs()
    opening = asyncio.ensure_future(_opened(tmp_git_repo, repository))
    await asyncio.wait_for(repository.staging.wait(), SETTLE_SECONDS)

    opening.cancel()

    with pytest.raises(asyncio.CancelledError):
        await opening

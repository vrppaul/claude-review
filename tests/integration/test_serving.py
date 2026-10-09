"""A review held open in this process: what it hands back, whatever else goes wrong while it runs."""

import asyncio
import tempfile
from pathlib import Path

import pytest
from httpx import AsyncClient
from structlog.typing import EventDict
from websockets.asyncio.client import connect

from claude_review.hosting.ports import ANY_FREE_PORT
from claude_review.hosting.serving import serve_review
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.review.browser_presence import BrowserPresence
from claude_review.services.review_opening import ReviewOpening, open_diff
from claude_review.services.tree_watcher_service import TreeWatcherService
from tests.helpers import SESSION_ROUTE, SETTLE_SECONDS

SUBMIT_ROUTE = "/api/submit"
# How an address to the review becomes one its page's socket connects to
HTTP_SCHEME = "http://"
WEBSOCKET_SCHEME = "ws://"
THE_ROUND = "Rename the helper."
# The last round, sent and ending the review
LAST_ROUND = {"threads": [], "body": THE_ROUND, "end": True}


class RecordingAnnouncer:
    """Whoever started the review, as a test: it holds on to what it is told."""

    def __init__(self) -> None:
        self.address: asyncio.Future[str] = asyncio.get_running_loop().create_future()

    async def listening_at(self, url: str) -> None:
        self.address.set_result(url)

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
async def opening(tmp_git_repo: Path) -> ReviewOpening:
    (tmp_git_repo / "initial.txt").write_text("changed\n")
    return await open_diff(tmp_git_repo, None, GitRepository())


@pytest.fixture
async def announcer() -> RecordingAnnouncer:
    return RecordingAnnouncer()


def _session_address(address: str) -> str:
    """Where the page of the review at this address holds its session socket."""
    return f"{address.replace(HTTP_SCHEME, WEBSOCKET_SCHEME, 1)}{SESSION_ROUTE}"


def _events(logged: list[EventDict]) -> list[str]:
    return [entry["event"] for entry in logged]


async def test_a_watch_on_the_tree_that_fails_leaves_the_review_running_and_its_round_handed_back(
    opening: ReviewOpening, announcer: RecordingAnnouncer, logged: list[EventDict], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The watch only helps; the reader's unsent work and the last round matter more than it."""
    monkeypatch.setattr(TreeWatcherService, "changes", lambda *_arguments, **_keywords: FailingWatch())

    serving = asyncio.ensure_future(serve_review(opening, port=ANY_FREE_PORT, announcer=announcer))
    address = await asyncio.wait_for(announcer.address, SETTLE_SECONDS)
    # The tree is watched only once a page is there to be told
    async with connect(_session_address(address)), AsyncClient(base_url=address) as agent:
        await agent.post(SUBMIT_ROUTE, json=LAST_ROUND)

    assert THE_ROUND in await asyncio.wait_for(serving, timeout=SETTLE_SECONDS)
    assert "review_helper_failed" in _events(logged)


async def test_a_review_that_can_no_longer_tell_its_page_closed_ends_rather_than_running_for_good(
    opening: ReviewOpening, announcer: RecordingAnnouncer, logged: list[EventDict], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run on, it would hold its port and keep its agent waiting long after the reader has gone."""
    monkeypatch.setattr(BrowserPresence, "until_closed_for_good", _failing_check)

    handed_back = await asyncio.wait_for(
        serve_review(opening, port=ANY_FREE_PORT, announcer=announcer), timeout=SETTLE_SECONDS
    )

    assert handed_back == ""
    assert "review_part_failed" in _events(logged)

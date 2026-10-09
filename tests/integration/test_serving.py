"""A review held open in this process: what it hands back, whatever else goes wrong while it runs."""

import asyncio
import socket
import tempfile
from pathlib import Path

import pytest
from httpx import AsyncClient, HTTPError

from claude_review.hosting.address import LOOPBACK, review_url
from claude_review.hosting.ports import ANY_FREE_PORT
from claude_review.hosting.serving import LaunchOptions, serve_review
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.review_opening import open_diff
from claude_review.services.tree_watcher_service import TreeWatcherService
from tests.helpers import CONTEXT_ROUTE, LOOK_EVERY_SECONDS, SETTLE_SECONDS

THE_ROUND = "Rename the helper."


class ChangesThatFail:
    """A watch on the tree that fails the first time it looks, as a disk gone away would."""

    def __aiter__(self) -> ChangesThatFail:
        return self

    async def __anext__(self) -> int:
        failure = "the disk went away"
        raise OSError(failure)


@pytest.fixture(autouse=True)
def kept_under_this_test(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep what the review writes, and what it remembers about its reader, under this test's own directory."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))


@pytest.fixture
def free_port() -> int:
    with socket.socket() as probe:
        probe.bind((LOOPBACK, ANY_FREE_PORT))
        return probe.getsockname()[1]


async def _until_it_answers(agent: AsyncClient) -> None:
    deadline = asyncio.get_running_loop().time() + SETTLE_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        try:
            await agent.get(CONTEXT_ROUTE)
        except HTTPError:
            await asyncio.sleep(LOOK_EVERY_SECONDS)
        else:
            return
    failure = "the review never answered"
    raise AssertionError(failure)


async def test_a_watch_on_the_tree_that_fails_leaves_the_review_running_and_its_round_handed_back(
    tmp_git_repo: Path, free_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The watch only helps; the reader's unsent work and the last round matter more than it."""
    (tmp_git_repo / "initial.txt").write_text("changed\n")
    monkeypatch.setattr(TreeWatcherService, "changes", lambda *_arguments, **_keywords: ChangesThatFail())
    opening = await open_diff(tmp_git_repo, None, GitRepository())

    serving = asyncio.ensure_future(serve_review(opening, LaunchOptions(port=free_port, open_browser=False)))
    async with AsyncClient(base_url=review_url(free_port)) as agent:
        await _until_it_answers(agent)
        await agent.post("/api/submit", json={"threads": [], "body": THE_ROUND, "end": True})

    assert THE_ROUND in await asyncio.wait_for(serving, timeout=SETTLE_SECONDS)

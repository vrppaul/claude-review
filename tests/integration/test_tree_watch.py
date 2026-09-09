"""Saying when the working tree has moved on under the review.

The review is a photograph of the tree at one moment. The agent goes on
changing files, and so does an editor or a rebase. Nothing here acts on
that: swapping the diff under someone mid-sentence orphans what they were
writing, and the decision costs one click.
"""

import asyncio
import contextlib
from pathlib import Path

from claude_review.repositories.git_repository import GitRepository
from claude_review.services.tree_watcher_service import TreeWatcherService


def _watcher() -> TreeWatcherService:
    return TreeWatcherService(git_repository=GitRepository(), poll_seconds=0.02)


async def _first(watcher: TreeWatcherService, root: Path, taken_at: frozenset[str], stop: asyncio.Event) -> int | None:
    """How many files the watcher reports moving, or nothing before it gives up."""
    changes = watcher.changes(root, taken_at=lambda: taken_at, stop=stop)
    try:
        return await asyncio.wait_for(anext(changes), timeout=5)
    except TimeoutError:
        return None
    finally:
        await changes.aclose()


async def test_a_file_changed_after_the_diff_is_reported(tmp_git_repo: Path) -> None:
    """What is on screen is no longer what is on disk, and the reader is told."""
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)

    (tmp_git_repo / "initial.txt").write_text("changed under the reader\n")

    assert await _first(watcher, tmp_git_repo, taken_at, asyncio.Event()) == 1


async def test_every_file_that_moved_is_counted_once(tmp_git_repo: Path) -> None:
    """A count is only useful if it says how much to go and look at."""
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)

    (tmp_git_repo / "initial.txt").write_text("one\n")
    (tmp_git_repo / "second.txt").write_text("two\n")

    assert await _first(watcher, tmp_git_repo, taken_at, asyncio.Event()) == 2


async def test_a_tree_that_has_not_moved_is_not_reported(tmp_git_repo: Path) -> None:
    """A notice for nothing is how a notice stops being read."""
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)

    assert await _first(watcher, tmp_git_repo, taken_at, asyncio.Event()) is None


async def test_a_change_is_reported_once_rather_than_every_poll(tmp_git_repo: Path) -> None:
    """Twice a second, the same sentence, is noise while somebody edits."""
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)
    (tmp_git_repo / "initial.txt").write_text("changed\n")

    stop = asyncio.Event()
    changes = watcher.changes(tmp_git_repo, taken_at=lambda: taken_at, stop=stop)
    try:
        assert await asyncio.wait_for(anext(changes), timeout=5) == 1
        second = asyncio.ensure_future(anext(changes))
        done, _ = await asyncio.wait({second}, timeout=0.5)
        assert not done, "the same change was reported twice"
        # Let the poll it is in the middle of finish before closing it
        second.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await second
    finally:
        await changes.aclose()

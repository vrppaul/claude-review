"""Saying when the working tree has moved on under the review.

The review is a photograph of the tree at one moment. The agent goes on
changing files, and so does an editor or a rebase. Nothing here acts on
that: swapping the diff under someone mid-sentence orphans what they were
writing, and the decision costs one click.
"""

import asyncio
import contextlib
from pathlib import Path

from claude_review.domain.models import TreeState
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.review.review_lifetime import ReviewLifetime
from claude_review.services.tree_watcher_service import TreeWatcherService
from tests.helpers import git

POLL_SECONDS = 0.02
# Long enough for a change to be seen however busy the machine is
REPORT_TIMEOUT_SECONDS = 5
# Enough polls to have seen a change had there been one
QUIET_POLLS = 25


def _watcher() -> TreeWatcherService:
    return TreeWatcherService(git_repository=GitRepository(objects=None), poll_seconds=POLL_SECONDS)


async def _first(
    watcher: TreeWatcherService, root: Path, taken_at: TreeState, *, give_up_after: float = REPORT_TIMEOUT_SECONDS
) -> int | None:
    """How many files the watcher reports moving, or nothing before it gives up."""
    changes = watcher.changes(root, taken_at=lambda: taken_at, lifetime=ReviewLifetime())
    try:
        return await asyncio.wait_for(anext(changes), timeout=give_up_after)
    except TimeoutError:
        return None
    finally:
        await changes.aclose()


async def _quiet(watcher: TreeWatcherService, root: Path, taken_at: TreeState) -> bool:
    """Whether the watcher stays silent for as many polls as it takes to notice anything."""
    return await _first(watcher, root, taken_at, give_up_after=POLL_SECONDS * QUIET_POLLS) is None


async def test_a_file_changed_after_the_diff_is_reported(tmp_git_repo: Path) -> None:
    """What is on screen is no longer what is on disk, and the reader is told."""
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)

    (tmp_git_repo / "initial.txt").write_text("changed under the reader\n")

    assert await _first(watcher, tmp_git_repo, taken_at) == 1


async def test_every_file_that_moved_is_counted_once(tmp_git_repo: Path) -> None:
    """A count is only useful if it says how much to go and look at."""
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)

    moved = ["initial.txt", "second.txt"]
    for name in moved:
        (tmp_git_repo / name).write_text(f"{name} moved\n")

    assert await _first(watcher, tmp_git_repo, taken_at) == len(moved)


async def test_a_tree_that_has_not_moved_is_not_reported(tmp_git_repo: Path) -> None:
    """A notice for nothing is how a notice stops being read."""
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)

    assert await _quiet(watcher, tmp_git_repo, taken_at)


async def test_a_change_is_reported_once_rather_than_every_poll(tmp_git_repo: Path) -> None:
    """Twice a second, the same sentence, is noise while somebody edits."""
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)
    (tmp_git_repo / "initial.txt").write_text("changed\n")

    changes = watcher.changes(tmp_git_repo, taken_at=lambda: taken_at, lifetime=ReviewLifetime())
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


async def test_a_file_changed_again_is_reported(tmp_git_repo: Path) -> None:
    """The agent rewriting a file already in the diff is the change that matters most."""
    (tmp_git_repo / "initial.txt").write_text("first rewrite\n")
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)

    (tmp_git_repo / "initial.txt").write_text("second rewrite, longer than the first\n")

    assert await _first(watcher, tmp_git_repo, taken_at) == 1


async def test_a_new_file_in_a_new_directory_is_reported(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "notes").mkdir()
    (tmp_git_repo / "notes" / "one.md").write_text("one\n")
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)

    (tmp_git_repo / "notes" / "two.md").write_text("two\n")

    assert await _first(watcher, tmp_git_repo, taken_at) == 1


async def test_staging_a_change_moves_nothing(tmp_git_repo: Path) -> None:
    """The diff on screen already holds the change; the index is not what is reviewed."""
    (tmp_git_repo / "initial.txt").write_text("changed\n")
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)

    git(tmp_git_repo, "add", "initial.txt")

    assert await _quiet(watcher, tmp_git_repo, taken_at)

"""Saying when the working tree has moved on under the review.

The review is a photograph of the tree at one moment. The agent goes on
changing files, and so does an editor or a rebase. Nothing here acts on
that: swapping the diff under someone mid-sentence orphans what they were
writing, and the decision costs one click.
"""

import asyncio
import contextlib
import os
from pathlib import Path

from claude_review.domain.interfaces import GitError
from claude_review.domain.models import TreeState
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.review.review_lifetime import ReviewLifetime
from claude_review.services.review.tree_watcher_service import TreeWatcherService, files_moved
from tests.helpers import LOOK_EVERY_SECONDS, RecordingPage, git

POLL_SECONDS = 0.02
# Long enough for a change to be seen however busy the machine is
REPORT_TIMEOUT_SECONDS = 5
# Enough polls to have seen a change had there been one
QUIET_POLLS = 25
# A file anyone may run, and one only its owner may read and write
RUNNABLE = 0o755
READ_BY_ITS_OWNER_ALONE = 0o600
# How much later than the diff a file is saved, in the nanoseconds a file's time is kept in
SAVED_LATER_NS = 1_000_000_000


class CountingGit(GitRepository):
    """Git as the watcher reads it, counting each time the watcher asks what has changed."""

    def __init__(self) -> None:
        super().__init__(objects=None)
        self.polls = 0

    async def changed_paths(self, path: Path) -> list[str]:
        self.polls += 1
        return await super().changed_paths(path)


async def _as_git_says(listed: list[str]) -> list[str]:
    return listed


async def _cannot_say(_listed: list[str]) -> list[str]:
    """What git mid-rebase answers: not what has changed, but that it cannot say."""
    msg = "index.lock exists"
    raise GitError(msg)


# The poll git cannot answer, one after the watcher has looked once, and what it answers then
FAILING_POLL = 2
ANSWER_ON_POLL = {FAILING_POLL: _cannot_say}


class GitThatFailsOnce(CountingGit):
    """Git that cannot say what has changed the second time it is asked, as one mid-rebase cannot."""

    async def changed_paths(self, path: Path) -> list[str]:
        listed = await super().changed_paths(path)
        return await ANSWER_ON_POLL.get(self.polls, _as_git_says)(listed)


def _watcher() -> TreeWatcherService:
    return TreeWatcherService(GitRepository(objects=None), poll_seconds=POLL_SECONDS)


async def _first(
    watcher: TreeWatcherService, root: Path, taken_at: TreeState, *, give_up_after: float = REPORT_TIMEOUT_SECONDS
) -> int | None:
    """How many files the watcher reports moving, or nothing before it gives up."""
    changes = watcher.changes(root, since=taken_at, lifetime=ReviewLifetime(RecordingPage()))
    try:
        return files_moved(await asyncio.wait_for(anext(changes), timeout=give_up_after), taken_at)
    except TimeoutError:
        return None
    finally:
        await changes.aclose()


async def _quiet(root: Path, taken_at: TreeState, repository: CountingGit) -> bool:
    """Whether the watcher stays silent for as many polls as it takes to notice anything.

    Counted in polls, not in seconds: a busy machine polls less often, and a
    watcher given too few looks would pass for one that saw nothing.
    """
    watcher = TreeWatcherService(repository, poll_seconds=POLL_SECONDS)
    changes = watcher.changes(root, since=taken_at, lifetime=ReviewLifetime(RecordingPage()))
    reported = asyncio.ensure_future(anext(changes))
    try:
        async with asyncio.timeout(REPORT_TIMEOUT_SECONDS):
            while repository.polls < QUIET_POLLS and not reported.done():
                await asyncio.sleep(LOOK_EVERY_SECONDS)
        return not reported.done()
    finally:
        reported.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reported
        await changes.aclose()


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

    assert await _quiet(tmp_git_repo, taken_at, CountingGit())


async def test_a_tree_git_cannot_read_for_a_moment_has_not_moved(tmp_git_repo: Path) -> None:
    """A repository mid-rebase says nothing of its files: that is no news of them."""
    (tmp_git_repo / "initial.txt").write_text("changed before the diff\n")
    taken_at = await _watcher().read(tmp_git_repo)

    assert await _quiet(tmp_git_repo, taken_at, GitThatFailsOnce())


async def test_a_tree_gone_back_to_how_it_stood_is_reported(tmp_git_repo: Path) -> None:
    """Whoever was told it moved is told it moved back: a file made and then removed leaves nothing moved."""
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)
    made = tmp_git_repo / "scratch.txt"

    changes = watcher.changes(tmp_git_repo, since=taken_at, lifetime=ReviewLifetime(RecordingPage()))
    try:
        made.write_text("for a moment\n")
        moved = await asyncio.wait_for(anext(changes), timeout=REPORT_TIMEOUT_SECONDS)
        made.unlink()
        back = await asyncio.wait_for(anext(changes), timeout=REPORT_TIMEOUT_SECONDS)
    finally:
        await changes.aclose()

    assert (files_moved(moved, taken_at), files_moved(back, taken_at)) == (1, 0)


async def test_a_change_is_reported_once_rather_than_every_poll(tmp_git_repo: Path) -> None:
    """Twice a second, the same sentence, is noise while somebody edits."""
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)
    (tmp_git_repo / "initial.txt").write_text("changed\n")

    changes = watcher.changes(tmp_git_repo, since=taken_at, lifetime=ReviewLifetime(RecordingPage()))
    try:
        assert files_moved(await asyncio.wait_for(anext(changes), timeout=5), taken_at) == 1
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


async def test_a_file_rewritten_to_the_same_length_is_reported(tmp_git_repo: Path) -> None:
    """Its size is as it was; only the time it was saved says it moved."""
    edited = tmp_git_repo / "initial.txt"
    edited.write_text("first rewrite\n")
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)

    edited.write_text("other rewrite\n")
    saved_at = edited.stat().st_mtime_ns + SAVED_LATER_NS
    os.utime(edited, ns=(saved_at, saved_at))

    assert await _first(watcher, tmp_git_repo, taken_at) == 1


async def test_a_new_file_in_a_new_directory_is_reported(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "notes").mkdir()
    (tmp_git_repo / "notes" / "one.md").write_text("one\n")
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)

    (tmp_git_repo / "notes" / "two.md").write_text("two\n")

    assert await _first(watcher, tmp_git_repo, taken_at) == 1


async def test_a_file_edited_in_a_new_directory_is_reported(tmp_git_repo: Path) -> None:
    """The directory holds the same files as before; only the file in it says it moved."""
    (tmp_git_repo / "notes").mkdir()
    (tmp_git_repo / "notes" / "one.md").write_text("one\n")
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)

    (tmp_git_repo / "notes" / "one.md").write_text("one, and more\n")

    assert await _first(watcher, tmp_git_repo, taken_at) == 1


async def test_looking_at_the_tree_leaves_the_repositorys_index_as_it_was(tmp_git_repo: Path) -> None:
    """The agent's own `git add` takes the index's lock; a look that wrote the index would take it first.

    A file saved again unchanged is what makes git want to write: the index
    still holds the time it had before.
    """
    saved = tmp_git_repo / "initial.txt"
    saved_at = saved.stat().st_mtime_ns + SAVED_LATER_NS
    os.utime(saved, ns=(saved_at, saved_at))
    index = tmp_git_repo / ".git" / "index"
    index_written_at = index.stat().st_mtime_ns

    await _watcher().read(tmp_git_repo)

    assert index.stat().st_mtime_ns == index_written_at


async def test_staging_a_change_moves_nothing(tmp_git_repo: Path) -> None:
    """The diff on screen already holds the change; the index is not what is reviewed."""
    (tmp_git_repo / "initial.txt").write_text("changed\n")
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)

    git(tmp_git_repo, "add", "initial.txt")

    assert await _quiet(tmp_git_repo, taken_at, CountingGit())


async def test_a_file_made_runnable_after_the_diff_is_reported(tmp_git_repo: Path) -> None:
    """Its content, size and time stay as they were, and the diff now shows a change of mode."""
    (tmp_git_repo / "initial.txt").write_text("already changed\n")
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)

    (tmp_git_repo / "initial.txt").chmod(RUNNABLE)

    assert await watcher.drift(tmp_git_repo, taken_at) == 1


async def test_a_permission_git_does_not_keep_moves_nothing(tmp_git_repo: Path) -> None:
    """Git keeps whether a file runs, nothing else of its mode: the diff stays as it was."""
    (tmp_git_repo / "initial.txt").write_text("already changed\n")
    watcher = _watcher()
    taken_at = await watcher.read(tmp_git_repo)

    (tmp_git_repo / "initial.txt").chmod(READ_BY_ITS_OWNER_ALONE)

    assert await watcher.drift(tmp_git_repo, taken_at) == 0

"""Noticing that the working tree has moved on since the diff was taken.

The agent changes files while the review is being read, and so does an
editor, a rebase or a stash. The review cannot tell the difference and does
not need to: all it has to say is that what is on screen is no longer what
is on disk, and let the reader decide when to take it again. Swapping the
diff under someone mid-sentence orphans what they were writing.
"""

import asyncio
import stat
from collections.abc import AsyncGenerator, Callable
from pathlib import Path

import structlog

from claude_review.domain.interfaces import GitError, Repository
from claude_review.domain.models import PathState, TreeState
from claude_review.services.review.review_lifetime import ReviewLifetime

log = structlog.get_logger()

# Twice a second: fast enough that saving a file and looking up feels
# immediate, slow enough that a `git status` costs nothing next to it.
POLL_SECONDS = 0.5


class TreeWatcherService:
    """Compare the working tree against the one the current diff was taken at."""

    def __init__(self, repository: Repository, poll_seconds: float = POLL_SECONDS) -> None:
        self._repository = repository
        self._poll_seconds = poll_seconds

    async def read(self, root: Path) -> TreeState:
        """Take the tree as it stands, to compare against later."""
        try:
            paths = await self._repository.changed_paths(root)
        except GitError:
            # A repository mid-rebase answers nothing useful; asking again in
            # half a second is better than treating that as a change
            log.warning("tree_status_failed", path=str(root))
            return frozenset()
        # Reading every file's size and time blocks, and the server has a
        # socket to keep answering on
        return await asyncio.to_thread(_tree_state, root, paths)

    async def drift(self, root: Path, taken_at: TreeState) -> int:
        """How many files have moved since the diff on screen was taken.

        The watcher says this once, to whoever is listening at the time. A
        review reloaded at that moment hears nothing, and one opened later
        never learns the tree moved before it arrived — so it has to be
        answerable on demand as well as pushable.
        """
        return len(_paths(await self.read(root) ^ taken_at))

    async def changes(
        self,
        root: Path,
        *,
        taken_at: Callable[[], TreeState],
        lifetime: ReviewLifetime,
    ) -> AsyncGenerator[int]:
        """Yield how many files have moved, each time the tree moves again, until the review ends.

        Once per change rather than once per poll: a notice that repeats every
        half second while somebody edits is noise, and the reader has already
        been told. `taken_at` is asked afresh every time, so retaking the diff
        settles the tree without the watcher being restarted.
        """
        told: TreeState | None = None

        while not await lifetime.ended_within(self._poll_seconds):
            current = await self.read(root)
            baseline = taken_at()

            if current == baseline:
                # Back to what the diff was taken at — by an undo, or because
                # the diff has just been retaken. Nothing to say, and the next
                # change deserves to be said afresh.
                told = None
                continue

            if current == told:
                continue

            told = current
            moved = _paths(current ^ baseline)
            log.info("tree_moved", file_count=len(moved))
            yield len(moved)


def _paths(tree: TreeState) -> set[str]:
    """The paths in a comparison, so a file counts once however it changed.

    A file that changed again is on both sides of it, with different sizes or
    times.
    """
    return {state.path for state in tree}


def _tree_state(root: Path, paths: list[str]) -> TreeState:
    return frozenset(_path_state(root, path) for path in paths)


def _path_state(root: Path, path: str) -> PathState:
    try:
        found = (root / path).stat()
    except OSError:
        return PathState(path=path, modified_ns=None, size=None, executable=None)
    return PathState(
        path=path,
        modified_ns=found.st_mtime_ns,
        size=found.st_size,
        executable=bool(found.st_mode & stat.S_IXUSR),
    )

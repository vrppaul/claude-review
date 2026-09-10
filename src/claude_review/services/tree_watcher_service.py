"""Noticing that the working tree has moved on since the diff was taken.

The agent changes files while the review is being read, and so does an
editor, a rebase or a stash. The review cannot tell the difference and does
not need to: all it has to say is that what is on screen is no longer what
is on disk, and let the reader decide when to take it again. Swapping the
diff under someone mid-sentence orphans what they were writing.
"""

import asyncio
from collections.abc import AsyncGenerator, Callable
from pathlib import Path

import structlog

from claude_review.domain.exceptions import GitError
from claude_review.domain.protocols import GitRepositoryProtocol

log = structlog.get_logger()

# Twice a second: fast enough that saving a file and looking up feels
# immediate, slow enough that a `git status` costs nothing next to it.
POLL_SECONDS = 0.5


class TreeWatcherService:
    """Compare the working tree against the one the current diff was taken at."""

    def __init__(self, git_repository: GitRepositoryProtocol, poll_seconds: float = POLL_SECONDS) -> None:
        self._git = git_repository
        self._poll_seconds = poll_seconds

    async def read(self, root: Path) -> frozenset[str]:
        """Take the tree as it stands, as a set of lines to compare later."""
        try:
            return frozenset(line for line in (await self._git.status(root)).splitlines() if line)
        except GitError:
            # A repository mid-rebase answers nothing useful; asking again in
            # half a second is better than treating that as a change
            log.warning("tree_status_failed", path=str(root))
            return frozenset()

    async def drift(self, root: Path, taken_at: frozenset[str]) -> int:
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
        taken_at: Callable[[], frozenset[str]],
        stop: asyncio.Event,
    ) -> AsyncGenerator[int]:
        """Yield how many files have moved, each time the tree moves again.

        Once per change rather than once per poll: a notice that repeats every
        half second while somebody edits is noise, and the reader has already
        been told. `taken_at` is asked afresh every time, so retaking the diff
        settles the tree without the watcher being restarted.
        """
        told: frozenset[str] | None = None

        while not stop.is_set():
            await asyncio.sleep(self._poll_seconds)
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


def _paths(lines: frozenset[str]) -> set[str]:
    """The paths in porcelain lines, so a file counts once however it changed.

    A line is two status letters, a space, then the path — and a file whose
    status changed appears on both sides of the comparison with different
    letters.
    """
    return {line[3:] for line in lines}

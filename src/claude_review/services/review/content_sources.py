"""Where a review's content comes from: a repository, taken again whenever asked, or files read once.

A review of a repository can be read against other bases, widened past its
hunks, taken again after a round and watched for the tree moving under it.
Files and a conversation can do none of that. Each kind of review answers
for itself here, so nothing else asks which kind it is.
"""

import asyncio
from pathlib import Path
from typing import Protocol

import structlog
from pydantic import BaseModel

from claude_review.domain.exceptions import NoRepositoryError
from claude_review.domain.models import ChangesSince, DiffFile, ReviewVersion
from claude_review.domain.page_events import TreeMoved
from claude_review.domain.protocols import Clock, PageChannel, RepositoryProtocol
from claude_review.services.diff_service import DiffService
from claude_review.services.file_window_service import FileWindow, FileWindowService
from claude_review.services.review.review_content import ReviewContent
from claude_review.services.review.review_lifetime import ReviewLifetime
from claude_review.services.review.review_versions import REVIEW_KEY, ReviewVersions
from claude_review.services.review.round_tracker import RoundTracker
from claude_review.services.review_opening import ReviewOpening
from claude_review.services.tree_watcher_service import TreeWatcherService

log = structlog.get_logger()


class DiffView(BaseModel):
    """The diff as the reader asked to see it, and how far the tree has moved since the review's own was taken."""

    files: list[DiffFile]
    # What the diff is compared against, as the header says it. None in a
    # review whose content did not come from a repository.
    phrase: str | None
    moved: int


class Retaken(BaseModel):
    """The diff taken again: how many files it holds, for which round, and which changed since that round began."""

    file_count: int
    round: int
    changes: ChangesSince | None


class ContentSource(Protocol):
    """What a review asks of where its content comes from."""

    @property
    def content(self) -> ReviewContent:
        """The take on screen now."""
        ...

    async def open(self) -> None:
        """Note what the review opens on: whatever later takes are measured against."""
        ...

    async def view(self, base_key: str | None, *, ignore_whitespace: bool) -> DiffView:
        """The diff against a base the review offers, with whitespace counted or not."""
        ...

    async def offer(self) -> list[ReviewVersion]:
        """The bases the diff can be read against."""
        ...

    async def retake(self) -> Retaken:
        """Take the diff again, after the work a round asked for."""
        ...

    async def file_window(self, path: str, start: int, end: int) -> FileWindow:
        """Lines a hunk left out, so the reader can widen its context."""
        ...

    async def tell_when_the_tree_moves(self, lifetime: ReviewLifetime) -> None:
        """Tell the pages each time the tree stops matching the take on screen, until the review ends."""
        ...


class RepositorySource:
    """The changes in a repository: taken at opening, taken again after each round, read against any base."""

    def __init__(
        self,
        opening: ReviewOpening,
        root: Path,
        *,
        repository: RepositoryProtocol,
        clock: Clock,
        rounds: RoundTracker,
        page: PageChannel,
    ) -> None:
        self._root = root
        self._base = opening.base
        self._content = ReviewContent(opening.diff_files, tree=frozenset())
        self._diffs = DiffService(git_repository=repository)
        self._watcher = TreeWatcherService(git_repository=repository)
        self._windows = FileWindowService(repository)
        self._versions = ReviewVersions(repository, clock, root, review_base=opening.base)
        self._rounds = rounds
        self._page = page
        # Held while the diff is taken again, so two retakes never interleave
        self._retaking = asyncio.Lock()

    @property
    def content(self) -> ReviewContent:
        return self._content

    async def open(self) -> None:
        """Note the tree the review opens on: what the watcher compares against, and a base rounds can go back to."""
        tree = await self._watcher.read(self._root)
        self._content = ReviewContent(self._content.files, tree)
        await self._versions.mark(self._rounds.current)

    async def view(self, base_key: str | None, *, ignore_whitespace: bool) -> DiffView:
        """The diff against a base, from git when only git can say it.

        Ignoring whitespace has to come from git, since only git knows which
        hunks vanish once whitespace stops counting; and a base names another
        version for the same working tree to be read against. Either way, what
        the review holds is left alone: a base is a way of looking, not a
        change to what is under review.
        """
        content = self._content
        files = content.files
        if base_key is not None or ignore_whitespace:
            against = await self._versions.resolve(base_key) if base_key is not None else self._base
            files = await self._diffs.get_diff(self._root, base=against, ignore_whitespace=ignore_whitespace)
        return DiffView(
            files=files,
            phrase=self._versions.phrase_of(base_key or REVIEW_KEY),
            moved=await self._watcher.drift(self._root, content.tree),
        )

    async def offer(self) -> list[ReviewVersion]:
        return await self._versions.offer()

    async def retake(self) -> Retaken:
        """Take the diff again, under the round it was taken in.

        One retake at a time, each about one round: a round sent while git is
        working must not tag this retake's mark with the round after it.
        """
        async with self._retaking:
            round_number = self._rounds.current
            # Asked before the new tree is written down, while the last mark is
            # still the one the diff on screen was taken at
            changes = await self._versions.changed_since_round_began(round_number)
            files = await self._diffs.get_diff(self._root, base=self._base)
            # Read after the diff, not before: a file saved in between then
            # belongs to the tree the diff was taken at, and the reader is not
            # told about a change that is already on their screen
            tree = await self._watcher.read(self._root)
            self._content = ReviewContent(files, tree)
            await self._versions.mark(round_number)

        log.info(
            "diff_retaken", file_count=len(files), round=round_number, changed=len(changes.paths) if changes else None
        )
        return Retaken(file_count=len(files), round=round_number, changes=changes)

    async def file_window(self, path: str, start: int, end: int) -> FileWindow:
        return await self._windows.read_window(self._root, path, start, end, in_review=self._content.paths)

    async def tell_when_the_tree_moves(self, lifetime: ReviewLifetime) -> None:
        """Say when the tree stops matching the diff. Never act on it: the reader decides when to take it again."""
        async for moved in self._watcher.changes(self._root, taken_at=lambda: self._content.tree, lifetime=lifetime):
            self._page.tell(TreeMoved(moved_count=moved))


class FixedSource:
    """Files or a conversation, read once: nothing to compare against, nothing to take again."""

    def __init__(self, opening: ReviewOpening) -> None:
        self._content = ReviewContent(opening.diff_files, tree=frozenset())

    @property
    def content(self) -> ReviewContent:
        return self._content

    async def open(self) -> None:
        """Nothing to note: what was read is all there will be."""

    async def view(self, base_key: str | None, *, ignore_whitespace: bool) -> DiffView:
        """The content as it was read; whitespace is part of it.

        Raises:
            NoRepositoryError: if a base is asked for.
        """
        if base_key is not None:
            msg = "This review is not compared against anything"
            raise NoRepositoryError(msg)
        return DiffView(files=self._content.files, phrase=None, moved=0)

    async def offer(self) -> list[ReviewVersion]:
        """No bases: not a failure, only nothing to choose between."""
        return []

    async def retake(self) -> Retaken:
        """Raises: NoRepositoryError, always."""
        msg = "No repository to retake the diff from"
        raise NoRepositoryError(msg)

    async def file_window(self, path: str, start: int, end: int) -> FileWindow:
        """Raises: NoRepositoryError, always."""
        msg = "No repository to read from"
        raise NoRepositoryError(msg)

    async def tell_when_the_tree_moves(self, lifetime: ReviewLifetime) -> None:
        """No tree to watch."""


def content_source(
    opening: ReviewOpening, *, repository: RepositoryProtocol, clock: Clock, rounds: RoundTracker, page: PageChannel
) -> ContentSource:
    """Where this review's content comes from: its repository, when it has one."""
    if opening.root is None:
        return FixedSource(opening)
    return RepositorySource(opening, opening.root, repository=repository, clock=clock, rounds=rounds, page=page)

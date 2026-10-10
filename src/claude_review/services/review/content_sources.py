"""Where a review's content comes from: a repository, taken again whenever asked, or files read once.

A review of a repository can be read against other bases, widened past its
hunks, taken again after a round and watched for the tree moving under it.
Files and a conversation can do none of that. Each kind of review answers
for itself here, so nothing else asks which kind it is.
"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol, override

import structlog
from pydantic import BaseModel

from claude_review.domain.exceptions import NoRepositoryError
from claude_review.domain.models import ChangedSinceRound, DiffFile, ReviewKey, VersionKey, VersionOnOffer
from claude_review.domain.protocols import Clock, GitError, RepositoryProtocol, StagedTreeProtocol
from claude_review.services.diff_reading import read_diff
from claude_review.services.file_window_service import FileWindow, FileWindowService
from claude_review.services.review.review_content import ReviewContent
from claude_review.services.review.review_lifetime import ReviewLifetime
from claude_review.services.review.review_versions import ReviewVersions
from claude_review.services.review.round_tracker import RoundTracker
from claude_review.services.review_opening import ReviewOpening
from claude_review.services.tree_watcher_service import TreeWatcherService

log = structlog.get_logger()


class DiffView(BaseModel):
    """The diff as the reader asked to see it, and how far the tree has moved since the review's own was taken."""

    files: list[DiffFile]
    # The base the diff was taken against. None in a review whose content did
    # not come from a repository: it is compared against nothing.
    shown: VersionKey | None
    moved: int


class Retaken(BaseModel):
    """The diff taken again: how many files it holds, for which round, and which changed since that round began."""

    file_count: int
    round: int
    changes: ChangedSinceRound | None


class ContentSource(Protocol):
    """What a review asks of where its content comes from."""

    @property
    def content(self) -> ReviewContent:
        """The take on screen now."""
        ...

    async def open(self) -> None:
        """Note what the review opens on: whatever later takes are measured against."""
        ...

    async def view(self, base: VersionKey | None, *, ignore_whitespace: bool) -> DiffView:
        """The diff against a base the review offers — its own when None — with whitespace counted or not."""
        ...

    async def offer(self) -> list[VersionOnOffer]:
        """The bases the diff can be read against."""
        ...

    async def retake(self) -> Retaken:
        """Take the diff again, after the work a round asked for."""
        ...

    async def file_window(self, path: str, start: int, end: int) -> FileWindow:
        """Lines a hunk left out, so the reader can widen its context."""
        ...

    def tree_moves(self, lifetime: ReviewLifetime) -> AsyncIterator[int]:
        """How many files have moved, each time the tree stops matching the take on screen, until the review ends."""
        ...


class RepositorySource(ContentSource):
    """The changes in a repository: taken at opening, taken again after each round, read against any base."""

    def __init__(
        self, opening: ReviewOpening, root: Path, *, repository: RepositoryProtocol, clock: Clock, rounds: RoundTracker
    ) -> None:
        self._root = root
        self._content = ReviewContent(opening.diff_files, tree=frozenset())
        self._repository = repository
        self._watcher = TreeWatcherService(git_repository=repository)
        self._windows = FileWindowService(repository)
        self._versions = ReviewVersions(repository, clock, root, review_base=opening.base)
        self._rounds = rounds
        # Held while the diff is taken again, so two retakes never interleave
        self._retaking = asyncio.Lock()

    @property
    @override
    def content(self) -> ReviewContent:
        return self._content

    @override
    async def open(self) -> None:
        """Take the diff the review opens on, and leave round one's mark from the same staging.

        Taken again here rather than kept from whoever read it first, so the
        mark rounds go back to is the very tree on screen. A repository git
        will not stage just now costs the review its first mark, never the
        review itself: what was read first stays on screen.
        """
        try:
            async with self._repository.staged(self._root) as staged:
                await self._take(staged, self._rounds.current)
        except GitError as refusal:
            log.warning("opening_mark_refused", reason=str(refusal))
            self._content = ReviewContent(self._content.files, await self._watcher.read(self._root))

    @override
    async def view(self, base: VersionKey | None, *, ignore_whitespace: bool) -> DiffView:
        """The diff against a base, from git when only git can say it.

        Ignoring whitespace has to come from git, since only git knows which
        hunks vanish once whitespace stops counting; and a base names another
        version for the same working tree to be read against. Either way, what
        the review holds is left alone: a base is a way of looking, not a
        change to what is under review.
        """
        content = self._content
        shown = base or ReviewKey()
        files = content.files
        # The review's own base, whitespace counted, is the diff it holds:
        # the one its threads are anchored to
        if shown != ReviewKey() or ignore_whitespace:
            against = await self._versions.resolve(shown)
            async with self._repository.staged(self._root) as staged:
                files = await read_diff(staged, base=against, ignore_whitespace=ignore_whitespace)
        return DiffView(files=files, shown=shown, moved=await self._watcher.drift(self._root, content.tree))

    @override
    async def offer(self) -> list[VersionOnOffer]:
        return await self._versions.offer()

    @override
    async def retake(self) -> Retaken:
        """Take the diff again, under the round it was taken in.

        One retake at a time, each about one round: a round sent while git is
        working must not tag this retake's mark with the round after it. One
        staging serves the whole of it, so the diff on screen, the tree
        written down and what changed since are all of the same tree.
        """
        async with self._retaking, self._repository.staged(self._root) as staged:
            round_number = self._rounds.current
            # Asked before the new tree is written down, while the last mark is
            # still the one the diff on screen was taken at
            changes = await self._versions.changed_since_round_began(round_number, staged)
            file_count = await self._take(staged, round_number)

        log.info(
            "diff_retaken", file_count=file_count, round=round_number, changed=len(changes.paths) if changes else None
        )
        return Retaken(file_count=file_count, round=round_number, changes=changes)

    async def _take(self, staged: StagedTreeProtocol, round_number: int) -> int:
        """Take the diff from a staging, put it on screen with its tree, mark it for the round; say how many files."""
        files = await read_diff(staged, base=self._versions.review_base, ignore_whitespace=False)
        # Read after the diff, not before: a file saved in between then
        # belongs to the tree the diff was taken at, and the reader is not
        # told about a change that is already on their screen
        tree = await self._watcher.read(self._root)
        self._content = ReviewContent(files, tree)
        await self._versions.mark(round_number, staged)
        return len(files)

    @override
    async def file_window(self, path: str, start: int, end: int) -> FileWindow:
        return await self._windows.read_window(self._root, path, start, end, in_review=self._content.paths)

    @override
    async def tree_moves(self, lifetime: ReviewLifetime) -> AsyncIterator[int]:
        async for moved in self._watcher.changes(self._root, taken_at=lambda: self._content.tree, lifetime=lifetime):
            yield moved


class FixedSource(ContentSource):
    """Files or a conversation, read once: nothing to compare against, nothing to take again."""

    def __init__(self, opening: ReviewOpening) -> None:
        self._content = ReviewContent(opening.diff_files, tree=frozenset())

    @property
    @override
    def content(self) -> ReviewContent:
        return self._content

    @override
    async def open(self) -> None:
        """Nothing to note: what was read is all there will be."""

    @override
    async def view(self, base: VersionKey | None, *, ignore_whitespace: bool) -> DiffView:
        """The content as it was read; whitespace is part of it.

        Raises:
            NoRepositoryError: if a base is asked for.
        """
        if base is not None:
            msg = "This review is not compared against anything"
            raise NoRepositoryError(msg)
        return DiffView(files=self._content.files, shown=None, moved=0)

    @override
    async def offer(self) -> list[VersionOnOffer]:
        """No bases: not a failure, only nothing to choose between."""
        return []

    @override
    async def retake(self) -> Retaken:
        """Raises: NoRepositoryError, always."""
        msg = "No repository to retake the diff from"
        raise NoRepositoryError(msg)

    @override
    async def file_window(self, path: str, start: int, end: int) -> FileWindow:
        """Raises: NoRepositoryError, always."""
        msg = "No repository to read from"
        raise NoRepositoryError(msg)

    @override
    async def tree_moves(self, lifetime: ReviewLifetime) -> AsyncIterator[int]:
        """No tree to watch: nothing in it ever moves."""
        for moved in ():
            yield moved


def content_source(
    opening: ReviewOpening, *, repository: RepositoryProtocol, clock: Clock, rounds: RoundTracker
) -> ContentSource:
    """Where this review's content comes from: its repository, when it has one."""
    if opening.root is None:
        return FixedSource(opening)
    return RepositorySource(opening, opening.root, repository=repository, clock=clock, rounds=rounds)

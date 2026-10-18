"""Where a review's content comes from: a repository, taken again whenever asked, or files read once.

A review of a repository can be read against other bases, widened past its
hunks, taken again after a round and watched for the tree moving under it.
Files and a conversation can do none of that. Each kind of review answers
for itself here, and its host picks the kind by what was opened
(`content_source`). The one thing the review asks a source about its kind
is whether its content is a change (`is_a_change`), once, as it makes its
story: what a story can be told of.

Either source holds the take on screen, a `ReviewContent`. A repository's
holds beside it what that take can be compared against, its
`ReviewVersions`, with what watches the tree for moving and what reads the
lines a hunk left out; a fixed source holds its one take alone. Neither
counts rounds: the review that does hands in the round each take is in.
"""

import asyncio
from abc import abstractmethod
from collections.abc import AsyncIterator
from typing import override

import structlog
from pydantic import BaseModel

from claude_review.domain.exceptions import NoRepositoryError
from claude_review.domain.interfaces import Clock, GitError, ReviewedRepository, StagedTree
from claude_review.domain.models import ChangedSinceRound, DiffFile, ReviewKey, VersionKey, VersionOnOffer
from claude_review.services.diff_reading import read_diff
from claude_review.services.file_window_service import FileWindow, FileWindowService
from claude_review.services.review.review_content import ReviewContent, TakesCompared
from claude_review.services.review.review_lifetime import ReviewLifetime
from claude_review.services.review.review_versions import ReviewVersions
from claude_review.services.review.tree_watcher_service import TreeWatcherService
from claude_review.services.review_opening import OpenedRepository, ReviewOpening
from claude_review.services.unified_diff import parse_unified_diff

log = structlog.get_logger()


class DiffView(BaseModel):
    """The diff as the reader asked to see it, and how far the tree has moved since the review's own was taken."""

    files: list[DiffFile]
    # The base the diff was taken against. None in a review whose content did
    # not come from a repository: it is compared against nothing.
    shown: VersionKey | None
    moved: int
    # The take the review held as this was read, whatever base it is read
    # against: the one the threads' lines are numbered by, and the one a
    # story must be of for its pieces to be numbered so too
    take: int


class Retaken(BaseModel):
    """The diff taken again: how many files it holds, for which round, and which changed since that round began."""

    file_count: int
    round: int
    changes: ChangedSinceRound | None


class ContentSource(TakesCompared):
    """What a review asks of where its content comes from: its takes, and what changed between two of them."""

    @property
    @abstractmethod
    def content(self) -> ReviewContent:
        """The take on screen now."""

    @property
    @abstractmethod
    def is_a_change(self) -> bool:
        """Whether the content is a change somebody made to a repository: what a story can be told of."""

    @abstractmethod
    async def open(self, round_number: int) -> None:
        """Note what the review opens on, in the round it opens in: whatever later takes are measured against."""

    @abstractmethod
    async def view(self, base: VersionKey | None, *, ignore_whitespace: bool) -> DiffView:
        """The diff against a base the review offers — its own when None — with whitespace counted or not."""

    @abstractmethod
    async def offer(self) -> list[VersionOnOffer]:
        """The bases the diff can be read against."""

    @abstractmethod
    async def retake(self, round_number: int) -> Retaken:
        """Take the diff again, after the work a round asked for, in the round it is taken in.

        One retake at a time: whoever owns the rounds waits for the one under
        way before it reads the round of the next and hands it in.
        """

    @abstractmethod
    async def file_window(self, path: str, start: int, end: int) -> FileWindow:
        """Lines a hunk left out, so the reader can widen its context."""

    @abstractmethod
    def tree_moves(self, lifetime: ReviewLifetime) -> AsyncIterator[int]:
        """How many files have moved, each time the tree stops matching the take on screen, until the review ends."""


class RepositorySource(ContentSource):
    """The changes in a repository: taken at opening, taken again after each round, read against any base."""

    def __init__(
        self, opening: ReviewOpening, opened: OpenedRepository, *, repository: ReviewedRepository, clock: Clock
    ) -> None:
        self._root = opened.root
        self._content = ReviewContent.opening_on(opening.diff_files)
        self._repository = repository
        self._watcher = TreeWatcherService(repository)
        self._windows = FileWindowService(repository)
        self._versions = ReviewVersions(repository, clock, opened)

    @property
    @override
    def content(self) -> ReviewContent:
        return self._content

    @property
    @override
    def is_a_change(self) -> bool:
        return True

    @override
    async def open(self, round_number: int) -> None:
        """Take the diff the review opens on, and leave the mark of the round it opens in from the same staging.

        Taken again here rather than kept from whoever read it first, so the
        mark rounds go back to is the very tree on screen. A repository git
        will not stage just now costs the review its first mark, never the
        review itself: what was read first stays on screen.
        """
        try:
            async with self._repository.staged(self._root) as staged:
                await self._take(staged, round_number)
        except GitError as refusal:
            log.warning("opening_mark_refused", reason=str(refusal))
            self._content = self._content.on_tree(await self._watcher.read(self._root))

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
        moved = await self._watcher.drift(self._root, content.tree)
        return DiffView(files=files, shown=shown, moved=moved, take=content.take)

    @override
    async def offer(self) -> list[VersionOnOffer]:
        return await self._versions.offer()

    @override
    async def retake(self, round_number: int) -> Retaken:
        """Take the diff again, under the round it is taken in.

        The round is handed in, a number, so a round sent while git is
        working cannot tag this retake's mark with the round after it. One
        staging serves the whole of it, so the diff on screen, the tree
        written down and what changed since are all of the same tree.
        """
        async with self._repository.staged(self._root) as staged:
            # Asked before the new tree is written down, while the last mark is
            # still the one the diff on screen was taken at
            changes = await self._versions.changed_since_round_began(round_number, staged)
            file_count = await self._take(staged, round_number)

        log.info(
            "diff_retaken", file_count=file_count, round=round_number, changed=len(changes.paths) if changes else None
        )
        return Retaken(file_count=file_count, round=round_number, changes=changes)

    @override
    async def changed_between(self, earlier: str, later: str) -> list[DiffFile]:
        """The diff from one take's tree to another's, parsed off the event loop as every diff here is."""
        raw = await self._repository.diff_between(self._root, earlier, later)
        return await asyncio.to_thread(parse_unified_diff, raw)

    async def _take(self, staged: StagedTree, round_number: int) -> int:
        """Take the diff from a staging, mark it for the round, put it on screen with its trees; say how many files."""
        files = await read_diff(staged, base=self._versions.pinned_base, ignore_whitespace=False)
        # Read after the diff, not before: a file saved in between then
        # belongs to the tree the diff was taken at, and the reader is not
        # told about a change that is already on their screen
        tree = await self._watcher.read(self._root)
        written_as = await self._versions.mark(round_number, staged)
        self._content = self._content.taken_again(files, tree, written_as=written_as)
        return len(files)

    @override
    async def file_window(self, path: str, start: int, end: int) -> FileWindow:
        return await self._windows.read_window(self._root, path, start, end, in_review=self._content.paths)

    @override
    def tree_moves(self, lifetime: ReviewLifetime) -> AsyncIterator[int]:
        return self._watcher.changes(self._root, taken_at=lambda: self._content.tree, lifetime=lifetime)


class FixedSource(ContentSource):
    """Files or a conversation, read once: nothing to compare against, nothing to take again."""

    def __init__(self, opening: ReviewOpening) -> None:
        self._content = ReviewContent.opening_on(opening.diff_files)

    @property
    @override
    def content(self) -> ReviewContent:
        return self._content

    @property
    @override
    def is_a_change(self) -> bool:
        return False

    @override
    async def open(self, round_number: int) -> None:
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
        return DiffView(files=self._content.files, shown=None, moved=0, take=self._content.take)

    @override
    async def offer(self) -> list[VersionOnOffer]:
        """No bases: not a failure, only nothing to choose between."""
        return []

    @override
    async def retake(self, round_number: int) -> Retaken:
        """Raises: NoRepositoryError, always."""
        msg = "No repository to retake the diff from"
        raise NoRepositoryError(msg)

    @override
    async def changed_between(self, earlier: str, later: str) -> list[DiffFile]:
        """Raises: NoRepositoryError, always: what was read once has no trees."""
        msg = "No repository to compare takes in"
        raise NoRepositoryError(msg)

    @override
    async def file_window(self, path: str, start: int, end: int) -> FileWindow:
        """Raises: NoRepositoryError, always."""
        msg = "No repository to read from"
        raise NoRepositoryError(msg)

    @override
    def tree_moves(self, lifetime: ReviewLifetime) -> AsyncIterator[int]:
        """No tree to watch: nothing in it ever moves."""
        return _no_moves()


async def _no_moves() -> AsyncIterator[int]:
    """The moves of a tree there is none of: an iterator that ends at once, having yielded nothing."""
    for moved in ():
        yield moved


def content_source(opening: ReviewOpening, *, repository: ReviewedRepository, clock: Clock) -> ContentSource:
    """Where this review's content comes from: its repository, when it has one."""
    if opening.repository is None:
        return FixedSource(opening)
    return RepositorySource(opening, opening.repository, repository=repository, clock=clock)

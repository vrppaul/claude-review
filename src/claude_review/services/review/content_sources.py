"""Where a review's content comes from: a repository, taken again whenever asked, or files read once.

A review of a repository can be read against other bases, widened past its
hunks, taken again after a round, watched for the tree moving under it,
asked where a name in it stands, and opened at a file the change did not touch.
Files and a conversation can do none of that. Each kind of review answers
for itself here, and its host picks the kind by what was opened
(`content_source`). The one thing the review asks a source about its kind
is whether its content is a change (`is_a_change`), once, as it makes its
story: what a story can be told of.

Either source holds the take on screen, a `ReviewContent`. A repository's
holds beside it what that take can be compared against, its
`ReviewVersions`, with what watches the tree for moving and what reads the
lines a hunk left out; a fixed source holds its one take alone. Neither
keeps a count of rounds: the review hands each take the round being written
to read (`RoundBeingWritten`), which a retake reads once its turn comes.
"""

import asyncio
from abc import abstractmethod
from collections.abc import AsyncIterator
from typing import assert_never, override

import structlog
from pydantic import BaseModel

from claude_review.domain.code_names import CodePlace, NameFound
from claude_review.domain.exceptions import NoRepositoryError, TakeNotWrittenError
from claude_review.domain.interfaces import Clock, GitError, ReviewedRepository, StagedTree
from claude_review.domain.models import (
    ChangedSinceRound,
    DiffFile,
    FileWindow,
    OfConversation,
    OfFiles,
    OpenedFileOfTake,
    ReviewKey,
    VersionKey,
    VersionOnOffer,
)
from claude_review.services.anchor_service import LineAnchorHandler, TakeRead, TakeUnread
from claude_review.services.code_names.lookup import NameLookup
from claude_review.services.diff_reading import read_diff, read_diff_between
from claude_review.services.files_of_take import FilesOfTake
from claude_review.services.review.review_checks import TreesWritten
from claude_review.services.review.review_content import ReviewContent, TakesCompared
from claude_review.services.review.review_lifetime import ReviewLifetime
from claude_review.services.review.review_versions import ReviewVersions
from claude_review.services.review.round_tracker import RoundBeingWritten
from claude_review.services.review.tree_watcher_service import TreeWatcherService, files_moved
from claude_review.services.review_opening import OpenedRepository, ReviewOpening

log = structlog.get_logger()


class DiffView(BaseModel):
    """The diff as the reader asked to see it, and how far the tree has moved since the review's own was taken."""

    files: list[DiffFile]
    # The files the review's own diff holds: `files` shows fewer under a narrower base or with whitespace left out
    own_paths: frozenset[str]
    # The files the review's own diff renamed, by the path each had: a path the agent may still name one by
    own_renames: dict[str, str]
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


class ContentSource(TakesCompared, TreesWritten):
    """What a review asks of where its content comes from: its takes, what changed between two, the tree written.

    It carries too the opening it was made from, which the review reads its
    name and kind from: made from one opening, it cannot be paired with another.
    """

    @property
    @abstractmethod
    def opening(self) -> ReviewOpening:
        """What the review was opened on, which this source was made from: the one place the review reads it."""

    @property
    @abstractmethod
    def content(self) -> ReviewContent:
        """The take on screen now."""

    @property
    @abstractmethod
    def is_a_change(self) -> bool:
        """Whether the content is a change somebody made to a repository: what a story can be told of."""

    @abstractmethod
    async def open(self, round_being_written: RoundBeingWritten) -> None:
        """Note what the review opens on, in the round being written: whatever later takes are measured against."""

    @abstractmethod
    async def view(self, base: VersionKey | None, *, ignore_whitespace: bool) -> DiffView:
        """The diff against a base the review offers — its own when None — with whitespace counted or not."""

    @abstractmethod
    async def offer(self) -> list[VersionOnOffer]:
        """The bases the diff can be read against."""

    @abstractmethod
    async def retake(self, round_being_written: RoundBeingWritten) -> Retaken:
        """Take the diff again after the work a round asked for, one retake at a time.

        Each is in the round being written as its turn comes.
        """

    @abstractmethod
    async def file_window(self, path: str, start: int, end: int) -> FileWindow:
        """Lines a hunk left out, so the reader can widen its context."""

    @abstractmethod
    async def name_at(self, place: CodePlace) -> NameFound:
        """The name at a place the reader points at, and every place it stands in the take on screen."""

    @abstractmethod
    async def file_of_take(self, path: str) -> OpenedFileOfTake:
        """A file of the take on screen as the reader opens it: whole, or saying why none of its lines are read."""

    @abstractmethod
    def base_holds(self, path: str) -> bool:
        """Whether the review's base holds a file at the path: what is told of every file the agent names."""

    @abstractmethod
    async def line_anchors(self, named: frozenset[str]) -> LineAnchorHandler:
        """Line anchors read against the take on screen, the new side of each of these files read whole."""

    @abstractmethod
    def tree_moves(self, lifetime: ReviewLifetime) -> AsyncIterator[int]:
        """How many files stand otherwise than in the take on screen, each time the tree changes, until the review ends.

        Zero, once the tree is back as the take holds it.
        """


class RepositorySource(ContentSource):
    """The changes in a repository: taken at opening, taken again after each round, read against any base."""

    def __init__(
        self, opening: ReviewOpening, opened: OpenedRepository, *, repository: ReviewedRepository, clock: Clock
    ) -> None:
        self._opening = opening
        self._root = opened.root
        self._content = ReviewContent.opening_on(opening.diff_files)
        self._repository = repository
        self._watcher = TreeWatcherService(repository)
        self._names = NameLookup(repository, opened.root)
        self._files_of_take = FilesOfTake(repository, opened.root)
        self._versions = ReviewVersions(repository, clock, opened)
        # Held while the diff is taken again, so two retakes never interleave
        self._retaking = asyncio.Lock()
        # Every file the pinned base holds, by path, listed as the review opens: none until then
        self._base_files: frozenset[str] = frozenset()

    @property
    @override
    def opening(self) -> ReviewOpening:
        return self._opening

    @property
    @override
    def content(self) -> ReviewContent:
        return self._content

    @property
    @override
    def is_a_change(self) -> bool:
        return True

    @override
    async def open(self, round_being_written: RoundBeingWritten) -> None:
        """Take the diff the review opens on, and leave the mark of the round being written from the same staging.

        Taken again here rather than kept from whoever read it first, so the
        mark rounds go back to is the very tree on screen. A repository git
        will not stage just now costs the review its first mark, never the
        review itself: what was read first stays on screen.

        The files of the base are listed once, after the staging lent the
        review's store the repository's objects: the base is pinned and never
        moves, so nothing the agent names waits on git to be told. The paths
        are kept for as long as the review: some 30 MB for a repository of
        200,000 files. A base git will not list holds no file, and what is
        named then goes only where the change holds it.
        """
        try:
            async with self._repository.staged(self._root) as staged:
                await self._take(staged, round_being_written.current)
        except GitError as refusal:
            log.warning("opening_mark_refused", reason=str(refusal))
            self._content = self._content.on_tree(await self._watcher.read(self._root))
        try:
            self._base_files = await self._repository.files_in(self._root, self._versions.pinned_base)
        except GitError as refusal:
            log.warning("base_files_unlisted", reason=str(refusal))

    @override
    async def view(self, base: VersionKey | None, *, ignore_whitespace: bool) -> DiffView:
        """The take on screen read against a base: a way of looking, which leaves what the review holds alone.

        Raises:
            UnknownVersionError: if the review offers no such base.
            TakeNotWrittenError: if git wrote down no tree of the take to read another way.
        """
        content = self._content
        shown = base or ReviewKey()
        files = content.files
        # The review's own base, whitespace counted, is the diff it holds: the one its threads are anchored to.
        # Any other reading is git's to say, of the tree the take was written down as and never the working
        # tree, so its lines are numbered as the review's own.
        if shown != ReviewKey() or ignore_whitespace:
            against = await self._versions.resolve(shown)
            files = await read_diff_between(
                self._repository, self._root, against, _tree_written(content), ignore_whitespace=ignore_whitespace
            )
        moved = await self._watcher.drift(self._root, content.tree)
        return DiffView(
            files=files,
            own_paths=content.paths,
            own_renames=content.renames,
            shown=shown,
            moved=moved,
            take=content.take,
        )

    @override
    async def offer(self) -> list[VersionOnOffer]:
        return await self._versions.offer(self._content.written_as)

    @override
    async def retake(self, round_being_written: RoundBeingWritten) -> Retaken:
        """Take the diff again, under the round it is taken in.

        One retake at a time, each about one round, read once its turn has
        come: a retake that waited is in the round sent while it did, and a
        round sent while git is working does not tag this retake's mark with
        the round after it. The round being written is handed in to read,
        never kept. One staging serves the whole of it, so the diff on
        screen, the tree written down and what changed since are all of the
        same tree.
        """
        async with self._retaking, self._repository.staged(self._root) as staged:
            round_number = round_being_written.current
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
        return await read_diff_between(self._repository, self._root, earlier, later, ignore_whitespace=False)

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
    async def tree_as_it_stands(self) -> str | None:
        """Written from a staging of its own, as the review's marks are: the tree a check ran on."""
        try:
            async with self._repository.staged(self._root) as staged:
                return await staged.write_tree()
        except GitError as refusal:
            log.warning("tree_not_written", reason=str(refusal))
            return None

    @override
    async def changed_since(self, trees: list[str]) -> dict[str, list[str]]:
        return await self._versions.changed_since(trees)

    @override
    async def file_window(self, path: str, start: int, end: int) -> FileWindow:
        """Read from the tree the take on screen was written down as, never the disk, so its lines are the diff's.

        Raises:
            TakeNotWrittenError: if git wrote down no tree of the take.
            LineRangeError: if the lines run backwards, or start below the first.
            FileNotInReviewError: if the take holds no file at the path.
            FileUnreadableError: if the review reads no lines of the file.
        """
        return await self._files_of_take.window(_tree_written(self._content), path, start, end)

    @override
    async def name_at(self, place: CodePlace) -> NameFound:
        """Read from the tree the take on screen was written down as, never the disk, so its lines are the diff's.

        Raises:
            TakeNotWrittenError: if git wrote down no tree of the take.
            FileNotInReviewError: if the side asked about has no file to read there.
            NoWordHereError: if the place holds no word.
        """
        content = self._content
        return await self._names.name_at(
            place, tree=_tree_written(content), base=self._versions.pinned_base, files=content.files
        )

    @override
    async def file_of_take(self, path: str) -> OpenedFileOfTake:
        """Read from the tree the take on screen was written down as, never the disk, so its lines are the diff's.

        Raises:
            TakeNotWrittenError: if git wrote down no tree of the take.
            FileNotInReviewError: if the take holds no file at the path.
        """
        return await self._files_of_take.file(_tree_written(self._content), path)

    @override
    def base_holds(self, path: str) -> bool:
        return path in self._base_files

    @override
    async def line_anchors(self, named: frozenset[str]) -> LineAnchorHandler:
        """The files read from the tree the take was written down as, in one asking; the diff alone where not."""
        content = self._content
        if content.written_as is None:
            return LineAnchorHandler(content.files, TakeUnread())
        try:
            take_files = await self._files_of_take.text_files(content.written_as, sorted(named))
        except GitError as refusal:
            # No thread is left unmoved for git's sake: they are read as where no tree was written down
            log.warning("take_files_unread", reason=str(refusal))
            return LineAnchorHandler(content.files, TakeUnread())
        return LineAnchorHandler(content.files, TakeRead(files=take_files))

    @override
    async def tree_moves(self, lifetime: ReviewLifetime) -> AsyncIterator[int]:
        """Measured against the take on screen as each change is heard, so a retake settles the tree unrestarted."""
        async for tree in self._watcher.changes(self._root, since=self._content.tree, lifetime=lifetime):
            moved = files_moved(tree, self._content.tree)
            log.info("tree_moved", file_count=moved)
            yield moved


class FixedSource(ContentSource):
    """Files or a conversation, read once: nothing to compare against, nothing to take again."""

    def __init__(self, opening: ReviewOpening) -> None:
        self._opening = opening
        self._content = ReviewContent.opening_on(opening.diff_files)

    @property
    @override
    def opening(self) -> ReviewOpening:
        return self._opening

    @property
    @override
    def content(self) -> ReviewContent:
        return self._content

    @property
    @override
    def is_a_change(self) -> bool:
        return False

    @override
    async def open(self, round_being_written: RoundBeingWritten) -> None:
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
        content = self._content
        return DiffView(
            files=content.files,
            own_paths=content.paths,
            own_renames=content.renames,
            shown=None,
            moved=0,
            take=content.take,
        )

    @override
    async def offer(self) -> list[VersionOnOffer]:
        """No bases: not a failure, only nothing to choose between."""
        return []

    @override
    async def retake(self, round_being_written: RoundBeingWritten) -> Retaken:
        """Raises: NoRepositoryError, always."""
        msg = "No repository to retake the diff from"
        raise NoRepositoryError(msg)

    @override
    async def changed_between(self, earlier: str, later: str) -> list[DiffFile]:
        """Raises: NoRepositoryError, always: what was read once has no trees."""
        msg = "No repository to compare takes in"
        raise NoRepositoryError(msg)

    @override
    async def tree_as_it_stands(self) -> str | None:
        """Raises: NoRepositoryError, always: what was read once has no tree."""
        msg = "No repository: no tree for a check to have run on"
        raise NoRepositoryError(msg)

    @override
    async def changed_since(self, trees: list[str]) -> dict[str, list[str]]:
        """Raises: NoRepositoryError, always: what was read once has no tree."""
        msg = "No repository to measure trees against"
        raise NoRepositoryError(msg)

    @override
    async def file_window(self, path: str, start: int, end: int) -> FileWindow:
        """Raises: NoRepositoryError, always."""
        msg = "No repository to read from"
        raise NoRepositoryError(msg)

    @override
    async def name_at(self, place: CodePlace) -> NameFound:
        """Raises: NoRepositoryError, always: what was read once has no tree to look a name up in."""
        msg = "No repository to look a name up in"
        raise NoRepositoryError(msg)

    @override
    async def file_of_take(self, path: str) -> OpenedFileOfTake:
        """Raises: NoRepositoryError, always: what was read once is every file there is to open."""
        msg = "No repository to open a file the review does not hold from"
        raise NoRepositoryError(msg)

    @override
    def base_holds(self, path: str) -> bool:
        """Never: what was read once has no base, and every file there is to read is one it read."""
        return False

    @override
    async def line_anchors(self, named: frozenset[str]) -> LineAnchorHandler:
        """What was read once is the whole take: a thread on a file it does not hold has lost its file."""
        return LineAnchorHandler(self._content.files, TakeRead(files=[]))

    @override
    def tree_moves(self, lifetime: ReviewLifetime) -> AsyncIterator[int]:
        """No tree to watch: nothing in it ever moves."""
        return _no_moves()


def _tree_written(content: ReviewContent) -> str:
    """The tree a take was written down as: what anything read of the take is read from.

    Raises:
        TakeNotWrittenError: if git wrote down none.
    """
    if content.written_as is None:
        msg = "git wrote down no tree of the take on screen: nothing in it can be read"
        raise TakeNotWrittenError(msg)
    return content.written_as


async def _no_moves() -> AsyncIterator[int]:
    """The moves of a tree there is none of: an iterator that ends at once, having yielded nothing."""
    for moved in ():
        yield moved


def content_source(opening: ReviewOpening, *, repository: ReviewedRepository, clock: Clock) -> ContentSource:
    """Where this review's content comes from: a repository's change from the repository, whenever it is taken."""
    match opening.source:
        case OpenedRepository() as opened:
            return RepositorySource(opening, opened, repository=repository, clock=clock)
        case OfFiles() | OfConversation():
            return FixedSource(opening)
        case _:
            assert_never(opening.source)

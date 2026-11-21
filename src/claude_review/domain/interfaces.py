"""What a review asks of the world around it: git, the disk, the clock, the pages open on it, and a reader's changes.

The services build on these and never on what implements them, which sits
in a layer the services do not import. Each is an abstract class its
implementations inherit, every member abstract, so a class that leaves one
out cannot be built.
"""

from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from pathlib import Path

from pydantic import BaseModel

from claude_review.domain.models import BlobsAt, Checkout, DiffFile, EpochMillis, FilesRead, GitRef
from claude_review.domain.page_events import PageEvent


class Clock(ABC):
    """Where the review reads the time, so whatever it dates can be dated by a clock a test sets."""

    @abstractmethod
    def now(self) -> EpochMillis:
        """The moment now, in epoch milliseconds."""


class GitError(Exception):
    """Raised when a git operation fails: the error every repository behind these interfaces raises."""


class StagedTree(ABC):
    """The working tree staged whole for one operation: everything git is asked within it reads the same index."""

    @abstractmethod
    async def diff(self, base: str, *, ignore_whitespace: bool) -> str:
        """The unified diff from a base to the working tree."""

    @abstractmethod
    async def write_tree(self) -> str:
        """Write the tree down and return its id."""

    @abstractmethod
    async def names_changed_since(self, bases: list[str]) -> dict[str, list[str]]:
        """For each base, the paths that differ from the working tree."""

    @abstractmethod
    async def too_large_to_show(self, base: str, files: list[DiffFile]) -> set[str]:
        """Of files the diff shows no lines of, those too large to read, in the base or the working tree, by path."""


class Repository(ABC):
    """A git repository: its working tree staged, its root, its changes, its refs and the commits they name."""

    @abstractmethod
    def staged(self, path: Path) -> AbstractAsyncContextManager[StagedTree]:
        """Stage the working tree of the repository at ``path`` for one operation."""

    @abstractmethod
    async def top_level(self, path: Path) -> Path | None:
        """Return the root of the repository containing ``path``, or None outside any."""

    @abstractmethod
    async def changed_paths(self, path: Path) -> list[str]:
        """Return every path where the working tree differs from HEAD, untracked files included."""

    @abstractmethod
    async def list_refs(self, path: Path) -> list[GitRef]:
        """Return the branches and tags that can be used as a base."""

    @abstractmethod
    async def commit_named(self, path: Path, revision: str) -> str | None:
        """Return the id of the commit a revision names now, or None when it names no commit."""

    @abstractmethod
    async def empty_tree(self, path: Path) -> str:
        """Return the id of the tree with nothing in it: what a repository with nothing committed is read against."""

    @abstractmethod
    async def checked_out(self, path: Path) -> Checkout:
        """Return what the working tree has checked out: its branch, or the commit HEAD names when it is on none."""

    @abstractmethod
    async def diff_between(self, path: Path, earlier: str, later: str, *, ignore_whitespace: bool) -> str:
        """The unified diff from a base or a tree a staging wrote down to such a tree: a take against either."""

    @abstractmethod
    async def names_changed_between(self, path: Path, earlier: list[str], later: str) -> dict[str, list[str]]:
        """For each base or tree written down that git will say it of, the paths that differ from such a tree.

        Raises:
            GitError: if no tree was ever written down to be read.
        """

    @abstractmethod
    async def too_large_between(self, path: Path, earlier: str, later: str, files: list[DiffFile]) -> set[str]:
        """Of files that diff shows no lines of, those too large to read, in the earlier or the later, by path."""


class TreesRead(ABC):
    """What a tree the review wrote down holds, read from the review's own object store and never from the disk.

    A commit is read as its tree, so a base the review opened on is read the same way.
    """

    @abstractmethod
    async def paths_holding(self, root: Path, tree: str, word: str) -> list[str]:
        """The paths of the tree's text files that hold the word whole, as git matches a whole word.

        Raises:
            GitError: if git cannot say it.
        """

    @abstractmethod
    async def paths_with_text(self, root: Path, tree: str, text: str) -> list[str]:
        """The paths of the tree's text files that hold the text anywhere, whatever its case.

        Raises:
            GitError: if git cannot say it.
        """

    @abstractmethod
    async def files_of(self, root: Path, tree: str, paths: list[str]) -> FilesRead:
        """What each of these files of the tree holds, by path; one larger than the review reads named and left unread.

        Raises:
            GitError: if git cannot say it.
        """

    @abstractmethod
    async def blobs_at(self, root: Path, tree: str, paths: list[str]) -> BlobsAt:
        """The id of what each of these files of the tree holds, by path, none of them read; one larger than the
        review reads named apart.

        Raises:
            GitError: if git cannot say it.
        """

    @abstractmethod
    async def blobs_read(self, root: Path, object_ids: list[str]) -> list[bytes]:
        """What each of these contents of the object store holds, in the order asked.

        Raises:
            GitError: if git cannot say it.
        """

    @abstractmethod
    async def files_in(self, root: Path, tree: str) -> frozenset[str]:
        """The path of every file the tree holds, however deep, none of them read.

        Raises:
            GitError: if git cannot say it.
        """


class OutlinesKept(ABC):
    """What the names outlining a file's content came to, kept across reviews by a key naming that content.

    A content's id never names other bytes, so what is kept by it never goes
    stale: a file is outlined once for as long as nobody changes it.
    """

    @abstractmethod
    async def read(self, keys: list[str]) -> dict[str, bytes]:
        """What is kept under each of these keys, by key; a key nothing is kept under is left out."""

    @abstractmethod
    async def keep(self, kept: dict[str, bytes]) -> None:
        """Keep each of these under its key, in place of what was kept there."""


class ReviewedRepository(Repository, TreesRead):
    """Everything a review asks of the repository it reviews."""


class PageChannel(ABC):
    """Where a review tells the pages open on it what has happened."""

    @abstractmethod
    def tell(self, event: PageEvent) -> None:
        """Tell every page open now, as things stand at this moment."""


class ImageStore(ABC):
    """Where a review keeps the images pasted into it."""

    @abstractmethod
    async def write(self, name: str, content: bytes) -> Path:
        """Write an image under a name the review chose, and return its path."""

    @abstractmethod
    async def remove(self, name: str) -> None:
        """Remove an image, if it is there."""


class RecordStore[Record: BaseModel](ABC):
    """Where one record is kept past a review's process: one about the reader, for every review, or a review's own."""

    @abstractmethod
    async def read(self) -> Record | None:
        """The record as last written, or None when none has been."""

    @abstractmethod
    async def write(self, record: Record) -> None:
        """Replace the record whole.

        Raises:
            OSError: if it cannot be written.
        """


class RecordChange[Record: BaseModel](ABC):
    """A change to one record about the reader: it knows what it carries, and so what it makes of the record."""

    @abstractmethod
    def applied_to(self, record: Record) -> Record:
        """The record as this change leaves it: what the change does not carry stays as it was kept."""

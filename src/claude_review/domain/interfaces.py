"""What a review asks of the world around it: git, the disk, the clock and the pages open on it.

The services build on these and never on what implements them, which sits
in a layer the services do not import. Each is an abstract class its
implementations inherit, every member abstract, so a class that leaves one
out cannot be built.
"""

from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from pathlib import Path

from pydantic import BaseModel

from claude_review.domain.models import EpochMillis, GitRef
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
    async def diff(self, base: str | None, *, ignore_whitespace: bool) -> str:
        """The unified diff from a base — HEAD when None — to the working tree."""

    @abstractmethod
    async def write_tree(self) -> str:
        """Write the tree down and return its id."""

    @abstractmethod
    async def names_changed_since(self, bases: list[str]) -> dict[str, list[str]]:
        """For each base, the paths that differ from the working tree."""


class Repository(ABC):
    """A git repository: its working tree staged, its root, its changes and its refs."""

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


class TrackedPaths(ABC):
    """Whether the repository keeps a file."""

    @abstractmethod
    async def is_tracked(self, root: Path, relative_path: str) -> bool:
        """Whether the repository tracks the file at this path."""


class ReviewedRepository(Repository, TrackedPaths):
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
    """Where one record about the reader is kept between reviews."""

    @abstractmethod
    async def read(self) -> Record | None:
        """The record as last written, or None when none has been."""

    @abstractmethod
    async def write(self, record: Record) -> None:
        """Replace the record whole."""

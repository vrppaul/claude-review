"""Domain protocols (interfaces) for claude-review."""

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

from claude_review.domain.models import EpochMillis, GitRef
from claude_review.domain.page_events import PageEvent


class Clock(Protocol):
    """Where the review reads the time, so whatever it dates can be dated by a clock a test sets."""

    def now(self) -> EpochMillis:
        """The moment now, in epoch milliseconds."""
        ...


class GitRepositoryProtocol(Protocol):
    """Protocol for git operations."""

    async def get_raw_diff(
        self,
        path: Path,
        base: str | None = None,
        *,
        ignore_whitespace: bool = False,
    ) -> str:
        """Return the raw unified diff output.

        If base is None: diff uncommitted changes against HEAD.
        If base is provided: diff from base to the current working tree.
        If ignore_whitespace: leave out changes that only alter whitespace.
        """
        ...

    async def top_level(self, path: Path) -> Path | None:
        """Return the root of the repository containing ``path``, or None outside any."""
        ...

    async def changed_paths(self, path: Path) -> list[str]:
        """Return every path where the working tree differs from HEAD, untracked files included."""
        ...

    async def snapshot(self, path: Path) -> str:
        """Write the working tree as it stands and return the tree's id."""
        ...

    async def changed_since(self, path: Path, bases: list[str]) -> dict[str, list[str]]:
        """Return, for each base, the paths that differ from the working tree."""
        ...

    async def list_refs(self, path: Path) -> list[GitRef]:
        """Return the branches and tags that can be used as a base."""
        ...


class TrackedPathsProtocol(Protocol):
    """Protocol for asking whether the repository keeps a file."""

    async def is_tracked(self, root: Path, relative_path: str) -> bool:
        """Whether the repository tracks the file at this path."""
        ...


class RepositoryProtocol(GitRepositoryProtocol, TrackedPathsProtocol, Protocol):
    """Everything a review asks of the repository it reviews."""


class PageChannel(Protocol):
    """Where a review tells the pages open on it what has happened."""

    def tell(self, event: PageEvent) -> None:
        """Tell every page open now, as things stand at this moment."""
        ...


class ImageStoreProtocol(Protocol):
    """Protocol for where a review keeps the images pasted into it."""

    async def write(self, name: str, content: bytes) -> Path:
        """Write an image under a name the review chose, and return its path."""
        ...

    async def remove(self, name: str) -> None:
        """Remove an image, if it is there."""
        ...


class RecordStoreProtocol[Record: BaseModel](Protocol):
    """Protocol for where one record about the reader is kept between reviews."""

    async def read(self) -> Record | None:
        """The record as last written, or None when none has been."""
        ...

    async def write(self, record: Record) -> None:
        """Replace the record whole."""
        ...

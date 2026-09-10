"""Domain protocols (interfaces) for claude-review."""

from pathlib import Path
from typing import Protocol

from claude_review.domain.models import GitRef


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

    async def status(self, path: Path) -> str:
        """Return what has changed in the working tree, one line per path."""
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

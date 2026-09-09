"""Domain protocols (interfaces) for claude-review."""

from pathlib import Path
from typing import Protocol


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

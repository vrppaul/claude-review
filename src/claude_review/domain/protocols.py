"""Domain protocols (interfaces) for claude-review."""

from pathlib import Path
from typing import Protocol


class GitRepositoryProtocol(Protocol):
    """Protocol for git operations."""

    async def get_raw_diff(self, path: Path, base: str | None = None) -> str:
        """Return the raw unified diff output.

        If base is None: diff uncommitted changes against HEAD.
        If base is provided: diff from base to the current working tree.
        """
        ...

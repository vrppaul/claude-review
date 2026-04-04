"""Domain protocols (interfaces) for claude-review."""

from pathlib import Path
from typing import Protocol


class GitRepositoryProtocol(Protocol):
    """Protocol for git operations."""

    async def get_raw_diff(self, path: Path) -> str:
        """Return the raw unified diff output for uncommitted changes."""
        ...

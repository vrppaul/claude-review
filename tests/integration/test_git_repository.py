"""Tests for GitRepository error handling."""

from pathlib import Path

import pytest

from claude_review.domain.exceptions import GitError
from claude_review.repositories.git_repository import GitRepository


async def test_git_error_on_non_git_directory(tmp_path: Path) -> None:
    """Running against a non-git directory raises GitError."""
    repo = GitRepository()

    with pytest.raises(GitError):
        await repo.get_raw_diff(tmp_path)


async def test_git_error_on_nonexistent_directory() -> None:
    """Running against a nonexistent directory raises GitError."""
    repo = GitRepository()

    with pytest.raises(GitError):
        await repo.get_raw_diff(Path("/tmp/nonexistent-repo-path-xyz"))

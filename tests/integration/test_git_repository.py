"""Tests for GitRepository error handling."""

from pathlib import Path

import pytest

from claude_review.domain.exceptions import GitError
from claude_review.repositories.git_repository import GitRepository
from tests.helpers import git


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


async def test_reading_a_diff_leaves_no_objects_behind(tmp_git_repo: Path) -> None:
    """Staging writes a blob per untracked file; none of them belong in the repo."""
    build = tmp_git_repo / "build"
    build.mkdir()
    for i in range(20):
        (build / f"gen_{i}.txt").write_text(f"unique {i}\n")

    objects = tmp_git_repo / ".git" / "objects"
    before = sum(1 for _ in objects.rglob("*") if _.is_file())

    diff = await GitRepository().get_raw_diff(tmp_git_repo)

    after = sum(1 for _ in objects.rglob("*") if _.is_file())
    assert "gen_0.txt" in diff, "the untracked files should still be in the review"
    assert after == before


async def test_reading_a_diff_leaves_the_staging_area_alone(tmp_git_repo: Path) -> None:
    """The review must not disturb what the developer has staged."""
    (tmp_git_repo / "staged.txt").write_text("on purpose\n")
    git(tmp_git_repo, "add", "staged.txt")
    (tmp_git_repo / "unstaged.txt").write_text("not yet\n")

    await GitRepository().get_raw_diff(tmp_git_repo)

    staged = git(tmp_git_repo, "diff", "--cached", "--name-only").split()
    assert staged == ["staged.txt"]

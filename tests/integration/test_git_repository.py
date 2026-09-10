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


async def test_what_changed_since_a_snapshot(tmp_git_repo: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    """A diff against a round's snapshot shows what happened after that round, and nothing else."""
    store = tmp_path_factory.mktemp("review-objects")
    repo = GitRepository(objects=store)
    (tmp_git_repo / "answered.txt").write_text("as asked\n")
    (tmp_git_repo / "untouched.txt").write_text("left alone\n")

    round_one = await repo.snapshot(tmp_git_repo)
    (tmp_git_repo / "answered.txt").write_text("as asked\nand then some\n")

    since_round_one = await repo.get_raw_diff(tmp_git_repo, base=round_one)
    whole_review = await repo.get_raw_diff(tmp_git_repo)

    assert "answered.txt" in since_round_one
    assert "untouched.txt" not in since_round_one, "it has not moved since the round was sent"
    assert "untouched.txt" in whole_review, "the review as a whole still holds it"


async def test_a_snapshot_outlives_the_call_that_took_it(
    tmp_git_repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Rounds are compared against trees taken hours earlier, by other requests."""
    store = tmp_path_factory.mktemp("review-objects")
    (tmp_git_repo / "work.txt").write_text("first pass\n")

    taken = await GitRepository(objects=store).snapshot(tmp_git_repo)
    (tmp_git_repo / "work.txt").write_text("second pass\n")
    later = await GitRepository(objects=store).get_raw_diff(tmp_git_repo, base=taken)

    assert "second pass" in later


async def test_a_snapshot_leaves_the_repository_alone(
    tmp_git_repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """A review's snapshots are its own; the repository under review gains nothing."""
    store = tmp_path_factory.mktemp("review-objects")
    (tmp_git_repo / "generated.txt").write_text("noise\n")
    objects = tmp_git_repo / ".git" / "objects"
    before = sum(1 for _ in objects.rglob("*") if _.is_file())

    await GitRepository(objects=store).snapshot(tmp_git_repo)

    after = sum(1 for _ in objects.rglob("*") if _.is_file())
    assert after == before


async def test_a_snapshot_is_refused_without_a_store_to_keep_it(tmp_git_repo: Path) -> None:
    """Written to a directory that is thrown away, a tree id names nothing."""
    with pytest.raises(GitError):
        await GitRepository().snapshot(tmp_git_repo)

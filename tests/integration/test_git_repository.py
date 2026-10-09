"""Tests for GitRepository error handling."""

from pathlib import Path

import pytest

from claude_review.domain.protocols import GitError
from claude_review.repositories.git_repository import GitRepository
from tests.helpers import git

# Enough untracked files that a stray blob per file would be plain to see
GENERATED_FILES = 20


async def _raw_diff(repository: GitRepository, path: Path, base: str | None = None) -> str:
    """What one staging of the working tree diffs as, against a base or HEAD."""
    async with repository.staged(path) as staged:
        return await staged.diff(base, ignore_whitespace=False)


async def _written_tree(repository: GitRepository, path: Path) -> str:
    """The id of the working tree, written down by one staging."""
    async with repository.staged(path) as staged:
        return await staged.write_tree()


def _object_count(objects: Path) -> int:
    """How many objects a repository holds, loose or packed."""
    return sum(1 for written in objects.rglob("*") if written.is_file())


async def test_git_error_on_non_git_directory(tmp_path: Path) -> None:
    """Running against a non-git directory raises GitError."""
    with pytest.raises(GitError):
        await _raw_diff(GitRepository(objects=None), tmp_path)


async def test_git_error_on_nonexistent_directory() -> None:
    """Running against a nonexistent directory raises GitError."""
    with pytest.raises(GitError):
        await _raw_diff(GitRepository(objects=None), Path("/tmp/nonexistent-repo-path-xyz"))


async def test_reading_a_diff_leaves_no_objects_behind(tmp_git_repo: Path) -> None:
    """Staging writes a blob per untracked file; none of them belong in the repo."""
    build = tmp_git_repo / "build"
    build.mkdir()
    for generated in range(GENERATED_FILES):
        (build / f"gen_{generated}.txt").write_text(f"unique {generated}\n")

    objects = tmp_git_repo / ".git" / "objects"
    before = _object_count(objects)

    diff = await _raw_diff(GitRepository(objects=None), tmp_git_repo)

    after = _object_count(objects)
    assert "gen_0.txt" in diff, "the untracked files should still be in the review"
    assert after == before


async def test_reading_a_diff_leaves_the_staging_area_alone(tmp_git_repo: Path) -> None:
    """The review must not disturb what the developer has staged."""
    (tmp_git_repo / "staged.txt").write_text("on purpose\n")
    git(tmp_git_repo, "add", "staged.txt")
    (tmp_git_repo / "unstaged.txt").write_text("not yet\n")

    await _raw_diff(GitRepository(objects=None), tmp_git_repo)

    staged = git(tmp_git_repo, "diff", "--cached", "--name-only").split()
    assert staged == ["staged.txt"]


async def test_what_changed_since_a_snapshot(tmp_git_repo: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    """A diff against a round's snapshot shows what happened after that round, and nothing else."""
    store = tmp_path_factory.mktemp("review-objects")
    repo = GitRepository(objects=store)
    (tmp_git_repo / "answered.txt").write_text("as asked\n")
    (tmp_git_repo / "untouched.txt").write_text("left alone\n")

    round_one = await _written_tree(repo, tmp_git_repo)
    (tmp_git_repo / "answered.txt").write_text("as asked\nand then some\n")

    since_round_one = await _raw_diff(repo, tmp_git_repo, base=round_one)
    whole_review = await _raw_diff(repo, tmp_git_repo)

    assert "answered.txt" in since_round_one
    assert "untouched.txt" not in since_round_one, "it has not moved since the round was sent"
    assert "untouched.txt" in whole_review, "the review as a whole still holds it"


async def test_a_snapshot_outlives_the_call_that_took_it(
    tmp_git_repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Rounds are compared against trees taken hours earlier, by other requests."""
    store = tmp_path_factory.mktemp("review-objects")
    (tmp_git_repo / "work.txt").write_text("first pass\n")

    taken = await _written_tree(GitRepository(objects=store), tmp_git_repo)
    (tmp_git_repo / "work.txt").write_text("second pass\n")
    later = await _raw_diff(GitRepository(objects=store), tmp_git_repo, base=taken)

    assert "second pass" in later


async def test_a_snapshot_leaves_the_repository_alone(
    tmp_git_repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """A review's snapshots are its own; the repository under review gains nothing."""
    store = tmp_path_factory.mktemp("review-objects")
    (tmp_git_repo / "generated.txt").write_text("noise\n")
    objects = tmp_git_repo / ".git" / "objects"
    before = _object_count(objects)

    await _written_tree(GitRepository(objects=store), tmp_git_repo)

    after = _object_count(objects)
    assert after == before


async def test_a_snapshot_is_refused_without_a_store_to_keep_it(tmp_git_repo: Path) -> None:
    """Written to a directory that is thrown away, a tree id names nothing."""
    with pytest.raises(GitError):
        await _written_tree(GitRepository(objects=None), tmp_git_repo)


async def test_a_file_the_reader_told_git_to_leave_alone_stays_out_of_the_diff(tmp_git_repo: Path) -> None:
    """The review reads the tree as `git diff` and `git status` do: an assume-unchanged file's edits are not news."""
    (tmp_git_repo / "initial.txt").write_text("edited locally, on purpose\n")
    git(tmp_git_repo, "update-index", "--assume-unchanged", "initial.txt")

    diff = await _raw_diff(GitRepository(objects=None), tmp_git_repo)

    assert "initial.txt" not in diff


async def test_one_staging_answers_every_question_about_the_same_tree(
    tmp_git_repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """The diff, the tree written down and what changed since agree, because they read one index."""
    repo = GitRepository(objects=tmp_path_factory.mktemp("review-objects"))
    (tmp_git_repo / "work.txt").write_text("first pass\n")
    earlier = await _written_tree(repo, tmp_git_repo)
    (tmp_git_repo / "work.txt").write_text("second pass\n")

    async with repo.staged(tmp_git_repo) as staged:
        diff = await staged.diff(earlier, ignore_whitespace=False)
        changed = await staged.names_changed_since([earlier])
        now = await staged.write_tree()

    assert "second pass" in diff
    assert changed == {earlier: ["work.txt"]}
    assert now != earlier

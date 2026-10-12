"""Tests for GitRepository error handling."""

import asyncio
import contextlib
import os
import signal
from pathlib import Path

import pytest

from claude_review.domain.interfaces import GitError
from claude_review.domain.models import HEAD, FileStatus
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_reading import read_diff
from tests.helpers import LOOK_EVERY_SECONDS, SETTLE_SECONDS, git

# A moment long before any test runs, in seconds since the epoch
SETTLED_AT = 1_000_000_000
# Enough untracked files that a stray blob per file would be plain to see
GENERATED_FILES = 20
# A git stuck on a huge tree: it writes down its process id, then works on without end
GIT_THAT_WORKS_ON = """#!/bin/sh
echo $$ > "{written_to}"
exec sleep 60
"""
# What a script needs to be run
RUNNABLE = 0o755


async def _raw_diff(repository: GitRepository, path: Path, base: str = HEAD) -> str:
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


async def test_git_error_on_nonexistent_directory(tmp_path: Path) -> None:
    """Running against a nonexistent directory raises GitError."""
    with pytest.raises(GitError):
        await _raw_diff(GitRepository(objects=None), tmp_path / "never-made")


def _running(process_id: int) -> bool:
    """Whether a process of this id is still there."""
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    return True


async def test_git_still_working_when_its_caller_gives_up_is_stopped_with_it(
    tmp_git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A review that ends while the watcher waits on git leaves no git working on behind it."""
    programs = tmp_path / "programs"
    programs.mkdir()
    written_to = tmp_path / "git-process"
    (programs / "git").write_text(GIT_THAT_WORKS_ON.format(written_to=written_to))
    (programs / "git").chmod(RUNNABLE)
    monkeypatch.setenv("PATH", f"{programs}{os.pathsep}{os.environ['PATH']}")
    looking = asyncio.ensure_future(GitRepository(objects=None).changed_paths(tmp_git_repo))
    async with asyncio.timeout(SETTLE_SECONDS):
        while not (written_to.exists() and written_to.read_text().strip()):
            await asyncio.sleep(LOOK_EVERY_SECONDS)
    git_process = int(written_to.read_text())

    looking.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await looking

    try:
        assert not _running(git_process)
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.kill(git_process, signal.SIGKILL)


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


@pytest.mark.parametrize("keeps_objects", [False, True], ids=["objects-thrown-away", "objects-kept"])
async def test_a_repository_whose_path_holds_a_colon_shows_its_changes_as_changes(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory, *, keeps_objects: bool
) -> None:
    """Git reads a list of object stores in its environment split on colons; a path holding one still lends its own.

    Lent nothing, the staging knows none of the repository's objects, and
    every file it tracks reads as added.
    """
    repo = tmp_path / "work:in progress"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    (repo / "tracked.txt").write_text("as committed\n")
    git(repo, "add", ".")
    git(repo, "-c", "user.email=test@test.com", "-c", "user.name=Test", "commit", "-m", "initial")
    (repo / "tracked.txt").write_text("as changed\n")
    store = tmp_path_factory.mktemp("review-objects") if keeps_objects else None

    async with GitRepository(objects=store).staged(repo) as staged:
        [changed] = await read_diff(staged, base=HEAD, ignore_whitespace=False)

    assert changed.path == "tracked.txt"
    assert changed.status == FileStatus.MODIFIED


async def test_a_file_saved_as_the_index_was_written_is_still_seen_changed(tmp_git_repo: Path) -> None:
    """Same size, same moment: only the index's own time tells git to look again, so the copy must keep it.

    The file is rewritten and given back the time the index knows it by, and
    the index is dated that same moment, so nothing but that comparison can
    tell git the file changed. Its ctime would; it is told not to trust it.
    """
    reviewed = tmp_git_repo / "settled.txt"
    reviewed.write_text("settled content\n")
    # Long settled before the commit, so git keeps its stat as trustworthy
    os.utime(reviewed, (SETTLED_AT, SETTLED_AT))
    git(tmp_git_repo, "config", "core.trustctime", "false")
    git(tmp_git_repo, "add", "settled.txt")
    git(tmp_git_repo, "commit", "-m", "settle")

    reviewed.write_text("settled CONTENT\n")
    os.utime(reviewed, (SETTLED_AT, SETTLED_AT))
    os.utime(tmp_git_repo / ".git" / "index", (SETTLED_AT, SETTLED_AT))

    diff = await _raw_diff(GitRepository(objects=None), tmp_git_repo)

    assert "settled CONTENT" in diff


async def test_a_base_that_reads_as_an_option_is_never_taken_for_one(
    tmp_git_repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """`--output=` would have git diff write a file wherever it names: a base is a revision, or nothing git reads."""
    target = tmp_path_factory.mktemp("outside") / "written-by-git"

    with pytest.raises(GitError):
        await _raw_diff(GitRepository(objects=None), tmp_git_repo, base=f"--output={target}")

    assert not target.exists()

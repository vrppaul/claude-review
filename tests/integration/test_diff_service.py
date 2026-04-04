"""Functional requirement tests for the diff service.

These test the actual user-facing behavior, not implementation details.
"""

from pathlib import Path

import pytest

from claude_review.domain.models import FileStatus, LineType
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_service import DiffService
from tests.helpers import git


@pytest.fixture
def diff_service() -> DiffService:
    return DiffService(git_repository=GitRepository())


async def test_diff_shows_all_changed_files(tmp_git_repo: Path, diff_service: DiffService) -> None:
    """Diff shows modified, added, and deleted files."""
    # Add a second file and commit so we can delete it later
    (tmp_git_repo / "to_delete.txt").write_text("will be deleted\n")
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "add file to delete")

    # Now make uncommitted changes: modify, add (staged), delete
    (tmp_git_repo / "initial.txt").write_text("modified content\n")
    (tmp_git_repo / "new_file.py").write_text("print('hello')\n")
    git(tmp_git_repo, "add", "new_file.py")
    (tmp_git_repo / "to_delete.txt").unlink()

    files = await diff_service.get_diff(tmp_git_repo)

    paths = {f.path for f in files}
    assert "initial.txt" in paths
    assert "new_file.py" in paths
    assert "to_delete.txt" in paths


async def test_diff_file_statuses(tmp_git_repo: Path, diff_service: DiffService) -> None:
    """Files have correct status indicators."""
    (tmp_git_repo / "initial.txt").write_text("modified\n")
    (tmp_git_repo / "brand_new.py").write_text("new\n")
    git(tmp_git_repo, "add", "brand_new.py")  # stage so git diff HEAD sees it

    files = await diff_service.get_diff(tmp_git_repo)
    by_path = {f.path: f for f in files}

    assert by_path["initial.txt"].status == FileStatus.MODIFIED
    assert by_path["brand_new.py"].status == FileStatus.ADDED


async def test_diff_includes_context_lines(tmp_git_repo: Path, diff_service: DiffService) -> None:
    """Hunks contain unmodified surrounding lines with correct line numbers."""
    # Create a file with multiple lines, modify one in the middle
    lines = [f"line {i}\n" for i in range(1, 11)]
    (tmp_git_repo / "multi.txt").write_text("".join(lines))
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "add multi-line file")

    lines[4] = "CHANGED line 5\n"
    (tmp_git_repo / "multi.txt").write_text("".join(lines))

    files = await diff_service.get_diff(tmp_git_repo)

    assert len(files) == 1
    hunk = files[0].hunks[0]

    context_lines = [line for line in hunk.lines if line.type == LineType.CONTEXT]
    assert len(context_lines) > 0, "Hunk should include context lines"

    # Context lines should have both old and new line numbers
    for line in context_lines:
        assert line.old_no is not None
        assert line.new_no is not None


async def test_added_deleted_modified_lines_typed_correctly(tmp_git_repo: Path, diff_service: DiffService) -> None:
    """Each line has correct type, old_no, new_no."""
    (tmp_git_repo / "initial.txt").write_text("replaced content\n")

    files = await diff_service.get_diff(tmp_git_repo)
    hunk = files[0].hunks[0]

    deleted = [dl for dl in hunk.lines if dl.type == LineType.DELETE]
    added = [al for al in hunk.lines if al.type == LineType.ADD]

    assert len(deleted) > 0
    assert len(added) > 0

    for line in deleted:
        assert line.old_no is not None
        assert line.new_no is None

    for line in added:
        assert line.old_no is None
        assert line.new_no is not None


async def test_git_repo_with_no_changes(tmp_git_repo: Path, diff_service: DiffService) -> None:
    """Returns empty file list when there are no uncommitted changes."""
    files = await diff_service.get_diff(tmp_git_repo)
    assert files == []


async def test_untracked_files_shown_as_added(tmp_git_repo: Path, diff_service: DiffService) -> None:
    """Untracked (new) files appear in diff as added."""
    (tmp_git_repo / "untracked.txt").write_text("untracked\n")

    files = await diff_service.get_diff(tmp_git_repo)

    assert len(files) == 1
    assert files[0].path == "untracked.txt"
    assert files[0].status == FileStatus.ADDED


async def test_deleted_file_status(tmp_git_repo: Path, diff_service: DiffService) -> None:
    """Deleted files show with DELETE status and all lines as deletions."""
    (tmp_git_repo / "initial.txt").unlink()

    files = await diff_service.get_diff(tmp_git_repo)

    assert len(files) == 1
    assert files[0].status == FileStatus.DELETED
    assert all(line.type == LineType.DELETE for line in files[0].hunks[0].lines)

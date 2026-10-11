"""Functional requirement tests for reading the diff.

These test the actual user-facing behavior, not implementation details.
"""

from pathlib import Path

import pytest

from claude_review.domain.interfaces import GitError
from claude_review.domain.models import HEAD, DiffFile, FileStatus, LineType
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_reading import read_diff
from tests.helpers import git


async def _diff(repo: Path, base: str = HEAD, *, ignore_whitespace: bool = False) -> list[DiffFile]:
    """The diff of a repository's working tree against a base, HEAD unless one is named."""
    async with GitRepository(objects=None).staged(repo) as staged:
        return await read_diff(staged, base=base, ignore_whitespace=ignore_whitespace)


async def test_diff_shows_all_changed_files(tmp_git_repo: Path) -> None:
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

    files = await _diff(tmp_git_repo)

    paths = {diff_file.path for diff_file in files}
    assert "initial.txt" in paths
    assert "new_file.py" in paths
    assert "to_delete.txt" in paths


async def test_diff_file_statuses(tmp_git_repo: Path) -> None:
    """Files have correct status indicators."""
    (tmp_git_repo / "initial.txt").write_text("modified\n")
    (tmp_git_repo / "brand_new.py").write_text("new\n")
    git(tmp_git_repo, "add", "brand_new.py")  # stage so git diff HEAD sees it

    files = await _diff(tmp_git_repo)
    by_path = {diff_file.path: diff_file for diff_file in files}

    assert by_path["initial.txt"].status == FileStatus.MODIFIED
    assert by_path["brand_new.py"].status == FileStatus.ADDED


async def test_diff_includes_context_lines(tmp_git_repo: Path) -> None:
    """Hunks contain unmodified surrounding lines with correct line numbers."""
    # Create a file with multiple lines, modify one in the middle
    lines = [f"line {line_number}\n" for line_number in range(1, 11)]
    (tmp_git_repo / "multi.txt").write_text("".join(lines))
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "add multi-line file")

    lines[4] = "CHANGED line 5\n"
    (tmp_git_repo / "multi.txt").write_text("".join(lines))

    files = await _diff(tmp_git_repo)

    assert len(files) == 1
    hunk = files[0].hunks[0]

    context_lines = [line for line in hunk.lines if line.kind == LineType.CONTEXT]
    assert len(context_lines) > 0, "Hunk should include context lines"

    # Context lines should have both old and new line numbers
    for line in context_lines:
        assert line.old_number is not None
        assert line.new_number is not None


async def test_added_deleted_modified_lines_typed_correctly(tmp_git_repo: Path) -> None:
    """Each line has correct type, old_number, new_number."""
    (tmp_git_repo / "initial.txt").write_text("replaced content\n")

    files = await _diff(tmp_git_repo)
    hunk = files[0].hunks[0]

    deleted = [line for line in hunk.lines if line.kind == LineType.DELETE]
    added = [line for line in hunk.lines if line.kind == LineType.ADD]

    assert len(deleted) > 0
    assert len(added) > 0

    for line in deleted:
        assert line.old_number is not None
        assert line.new_number is None

    for line in added:
        assert line.old_number is None
        assert line.new_number is not None


async def test_git_repo_with_no_changes(tmp_git_repo: Path) -> None:
    """Returns empty file list when there are no uncommitted changes."""
    files = await _diff(tmp_git_repo)
    assert files == []


async def test_untracked_files_shown_as_added(tmp_git_repo: Path) -> None:
    """Untracked (new) files appear in diff as added."""
    (tmp_git_repo / "untracked.txt").write_text("untracked\n")

    files = await _diff(tmp_git_repo)

    assert len(files) == 1
    assert files[0].path == "untracked.txt"
    assert files[0].status == FileStatus.ADDED


async def test_deleted_file_status(tmp_git_repo: Path) -> None:
    """Deleted files show with DELETE status and all lines as deletions."""
    (tmp_git_repo / "initial.txt").unlink()

    files = await _diff(tmp_git_repo)

    assert len(files) == 1
    assert files[0].status == FileStatus.DELETED
    assert all(line.kind == LineType.DELETE for line in files[0].hunks[0].lines)


async def test_base_shows_committed_changes(tmp_git_repo: Path) -> None:
    """--base shows changes committed after the base ref."""
    # Record the initial commit
    base = git(tmp_git_repo, "rev-parse", "HEAD").strip()

    # Make a second commit
    (tmp_git_repo / "second.py").write_text("print('hello')\n")
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "second commit")

    files = await _diff(tmp_git_repo, base=base)

    paths = {diff_file.path for diff_file in files}
    assert "second.py" in paths


async def test_base_includes_uncommitted_changes(tmp_git_repo: Path) -> None:
    """--base includes both committed and uncommitted changes."""
    base = git(tmp_git_repo, "rev-parse", "HEAD").strip()

    # Committed change
    (tmp_git_repo / "committed.py").write_text("committed\n")
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "add committed")

    # Uncommitted change
    (tmp_git_repo / "uncommitted.py").write_text("uncommitted\n")

    files = await _diff(tmp_git_repo, base=base)

    paths = {diff_file.path for diff_file in files}
    assert "committed.py" in paths
    assert "uncommitted.py" in paths


async def test_base_includes_untracked_files(tmp_git_repo: Path) -> None:
    """--base includes untracked files as additions."""
    base = git(tmp_git_repo, "rev-parse", "HEAD").strip()

    (tmp_git_repo / "untracked.txt").write_text("new file\n")

    files = await _diff(tmp_git_repo, base=base)

    assert len(files) == 1
    assert files[0].path == "untracked.txt"
    assert files[0].status == FileStatus.ADDED


async def test_invalid_base_raises_error(tmp_git_repo: Path) -> None:
    """Nonexistent base commit raises GitError."""
    with pytest.raises(GitError):
        await _diff(tmp_git_repo, base="nonexistent_ref_abc123")


async def test_diff_includes_files_with_non_ascii_names(tmp_git_repo: Path) -> None:
    """A file whose name has non-ASCII characters still appears in the review."""
    (tmp_git_repo / "документ.md").write_text("hello\n")
    (tmp_git_repo / "café.py").write_text("x = 1\n")

    files = await _diff(tmp_git_repo)

    paths = {diff_file.path for diff_file in files}
    assert "документ.md" in paths
    assert "café.py" in paths


async def test_diff_includes_files_with_spaces_in_names(tmp_git_repo: Path) -> None:
    """A file whose name contains spaces still appears in the review."""
    (tmp_git_repo / "my notes.md").write_text("todo\n")

    files = await _diff(tmp_git_repo)

    assert "my notes.md" in {diff_file.path for diff_file in files}


async def test_diff_reads_content_of_non_ascii_named_file(tmp_git_repo: Path) -> None:
    """Content of a non-ASCII named file is parsed, not just its path."""
    (tmp_git_repo / "заметки.txt").write_text("first line\nsecond line\n")

    files = await _diff(tmp_git_repo)
    by_path = {diff_file.path: diff_file for diff_file in files}

    contents = [line.content for hunk in by_path["заметки.txt"].hunks for line in hunk.lines]
    assert contents == ["first line", "second line"]


async def test_diff_handles_name_that_looks_like_a_diff_header(tmp_git_repo: Path) -> None:
    """A path containing " b/" does not confuse header parsing."""
    (tmp_git_repo / "a b").mkdir()
    (tmp_git_repo / "a b" / "c.py").write_text("x = 1\n")

    files = await _diff(tmp_git_repo)

    assert "a b/c.py" in {diff_file.path for diff_file in files}


async def test_diff_handles_quoted_name(tmp_git_repo: Path) -> None:
    """A path git has to quote is unquoted back to its real name."""
    (tmp_git_repo / 'weird"name.txt').write_text("content\n")

    files = await _diff(tmp_git_repo)

    assert 'weird"name.txt' in {diff_file.path for diff_file in files}


async def test_deleted_file_keeps_its_path(tmp_git_repo: Path) -> None:
    """A deleted file is named from the "---" side, since "+++" is /dev/null."""
    (tmp_git_repo / "初期.txt").write_text("content\n")
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "add file")
    (tmp_git_repo / "初期.txt").unlink()

    files = await _diff(tmp_git_repo)
    by_path = {diff_file.path: diff_file for diff_file in files}

    assert "初期.txt" in by_path
    assert by_path["初期.txt"].status == FileStatus.DELETED


async def test_binary_file_is_marked_as_binary(tmp_git_repo: Path) -> None:
    """A binary file appears in the review, flagged so the UI can explain the blank."""
    (tmp_git_repo / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x01\x02\x03")

    files = await _diff(tmp_git_repo)
    by_path = {diff_file.path: diff_file for diff_file in files}

    assert by_path["logo.png"].is_binary
    assert by_path["logo.png"].hunks == []


async def test_text_file_is_not_marked_as_binary(tmp_git_repo: Path) -> None:
    """A regular text change is not mistaken for binary."""
    (tmp_git_repo / "initial.txt").write_text("changed\n")

    files = await _diff(tmp_git_repo)
    by_path = {diff_file.path: diff_file for diff_file in files}

    assert not by_path["initial.txt"].is_binary


async def test_permission_change_reports_both_modes(tmp_git_repo: Path) -> None:
    """Making a file executable is visible even though no line changed."""
    script = tmp_git_repo / "run.sh"
    script.write_text("echo hi\n")
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "add script")
    script.chmod(0o755)

    files = await _diff(tmp_git_repo)
    by_path = {diff_file.path: diff_file for diff_file in files}

    assert by_path["run.sh"].old_mode == "100644"
    assert by_path["run.sh"].new_mode == "100755"


async def test_content_change_reports_no_mode_change(tmp_git_repo: Path) -> None:
    """A plain edit leaves the mode fields empty."""
    (tmp_git_repo / "initial.txt").write_text("changed\n")

    files = await _diff(tmp_git_repo)
    by_path = {diff_file.path: diff_file for diff_file in files}

    assert by_path["initial.txt"].old_mode is None
    assert by_path["initial.txt"].new_mode is None


async def test_renamed_file_is_listed_under_its_new_path(tmp_git_repo: Path) -> None:
    """A rename that also edits the file reports where the file is now."""
    original = tmp_git_repo / "old_name.txt"
    original.write_text("line one\nline two\nline three\n")
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "add file")

    git(tmp_git_repo, "mv", "old_name.txt", "new_name.txt")
    (tmp_git_repo / "new_name.txt").write_text("line one\nline two changed\nline three\n")

    files = await _diff(tmp_git_repo)
    paths = {diff_file.path for diff_file in files}

    assert "new_name.txt" in paths
    assert "old_name.txt" not in paths


async def test_pure_rename_is_listed_under_its_new_path(tmp_git_repo: Path) -> None:
    """A rename with no content change has no diff markers to read the path from."""
    (tmp_git_repo / "before.txt").write_text("unchanged content\n")
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "add file")
    git(tmp_git_repo, "mv", "before.txt", "after.txt")

    files = await _diff(tmp_git_repo)
    by_path = {diff_file.path: diff_file for diff_file in files}

    assert "after.txt" in by_path
    assert by_path["after.txt"].status == FileStatus.RENAMED


async def test_a_file_that_changed_type_is_shown_once(tmp_git_repo: Path) -> None:
    """A file turned into a link, and a link turned into a file: git writes each as two, the review shows one."""
    (tmp_git_repo / "target.txt").write_text("pointed at\n")
    (tmp_git_repo / "was_a_file.txt").write_text("one\ntwo\n")
    (tmp_git_repo / "was_a_link").symlink_to("target.txt")
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "a file and a link")
    (tmp_git_repo / "was_a_file.txt").unlink()
    (tmp_git_repo / "was_a_file.txt").symlink_to("target.txt")
    (tmp_git_repo / "was_a_link").unlink()
    (tmp_git_repo / "was_a_link").write_text("a file now\n")

    files = await _diff(tmp_git_repo)

    assert [diff_file.path for diff_file in files] == ["was_a_file.txt", "was_a_link"]
    assert all(diff_file.status == FileStatus.MODIFIED for diff_file in files)


async def test_binary_name_containing_a_header_separator(tmp_git_repo: Path) -> None:
    """A binary file has no markers, so its name must survive the header split."""
    (tmp_git_repo / "x b").mkdir()
    (tmp_git_repo / "x b" / "y.bin").write_bytes(b"\x00\x01\x02\xff\xfe")

    files = await _diff(tmp_git_repo)
    by_path = {diff_file.path: diff_file for diff_file in files}

    assert "x b/y.bin" in by_path
    assert by_path["x b/y.bin"].is_binary


async def test_mode_only_name_containing_a_header_separator(tmp_git_repo: Path) -> None:
    """A permission change has no markers either."""
    directory = tmp_git_repo / "x b"
    directory.mkdir()
    script = directory / "mode.txt"
    script.write_text("content\n")
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "add file")
    script.chmod(0o755)

    files = await _diff(tmp_git_repo)
    by_path = {diff_file.path: diff_file for diff_file in files}

    assert "x b/mode.txt" in by_path
    assert by_path["x b/mode.txt"].new_mode == "100755"


async def test_a_copied_file_is_shown_as_a_new_one(tmp_git_repo: Path) -> None:
    """A copy leaves the original in place, so what is new here is a file."""
    original = tmp_git_repo / "original.txt"
    original.write_text("".join(f"line {line_number}\n" for line_number in range(1, 30)))
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "add")
    git(tmp_git_repo, "config", "diff.renames", "copies")
    (tmp_git_repo / "copy.txt").write_text(original.read_text())

    files = await _diff(tmp_git_repo)
    by_path = {diff_file.path: diff_file for diff_file in files}

    assert "copy.txt" in by_path
    assert by_path["copy.txt"].status == FileStatus.ADDED


async def test_a_file_that_is_not_utf8_is_still_shown(tmp_git_repo: Path) -> None:
    """One file in another encoding costs its own odd characters, not the whole review."""
    (tmp_git_repo / "legacy.txt").write_bytes("café au lait\n".encode("latin-1"))

    [legacy] = [diff_file for diff_file in await _diff(tmp_git_repo) if diff_file.path == "legacy.txt"]

    assert legacy.hunks[0].lines[0].content.startswith("caf")


async def test_a_file_without_a_final_newline_shows_only_its_own_lines(tmp_git_repo: Path) -> None:
    """Git's "No newline at end of file" note is about the file, not a line of it."""
    (tmp_git_repo / "initial.txt").write_text("first\nlast, with no newline")

    [changed] = await _diff(tmp_git_repo)

    assert [line.content for line in changed.hunks[0].lines if line.kind == LineType.ADD] == [
        "first",
        "last, with no newline",
    ]
    assert [line.new_number for line in changed.hunks[0].lines if line.kind == LineType.ADD] == [1, 2]


@pytest.mark.parametrize(
    ("setting", "value"),
    [
        ("diff.mnemonicPrefix", "true"),
        ("diff.noprefix", "true"),
        ("color.diff", "always"),
        ("color.ui", "always"),
        ("diff.relative", "true"),
        # A diff tool of the reader's own, which must not stand in for git's format
        ("diff.external", "false"),
        ("core.quotePath", "false"),
    ],
)
async def test_the_readers_git_settings_do_not_change_what_is_shown(
    tmp_git_repo: Path, setting: str, value: str
) -> None:
    (tmp_git_repo / "a").mkdir()
    (tmp_git_repo / "a" / "inside.py").write_text("x = 1\n")
    (tmp_git_repo / "initial.txt").write_text("changed\n")
    git(tmp_git_repo, "config", setting, value)

    files = await _diff(tmp_git_repo)

    assert {diff_file.path for diff_file in files} == {"a/inside.py", "initial.txt"}
    assert all(diff_file.hunks for diff_file in files)

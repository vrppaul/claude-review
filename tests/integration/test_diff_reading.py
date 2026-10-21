"""Functional requirement tests for reading the diff.

These test the actual user-facing behavior, not implementation details.
"""

import asyncio
from pathlib import Path

import pytest

from claude_review.domain.interfaces import GitError
from claude_review.domain.models import HEAD, LARGEST_FILE_SHOWN_BYTES, DiffFile, FileStatus, LineType, Unshown
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_reading import read_diff
from tests.helpers import added_line, diff_file, git
from tests.without_git import StagingHeldStill

# A line of a generated log, and how many files of how many such lines make a
# diff that takes the parser a while to read
LOG_LINE = "00012345 a generated log line with some words in it"
FILES_IN_A_LARGE_DIFF = 40
LINES_PER_FILE = 500


def _large_change() -> list[DiffFile]:
    """Many added files of many lines."""
    lines = [added_line(number, LOG_LINE) for number in range(1, LINES_PER_FILE + 1)]
    return [diff_file(f"log_{number}.txt", lines, FileStatus.ADDED) for number in range(FILES_IN_A_LARGE_DIFF)]


async def _diff(repo: Path, base: str = HEAD, *, ignore_whitespace: bool = False) -> list[DiffFile]:
    """The diff of a repository's working tree against a base, HEAD unless one is named."""
    async with GitRepository(objects=None).staged(repo) as staged:
        return await read_diff(staged, base=base, ignore_whitespace=ignore_whitespace)


async def test_diff_file_statuses(tmp_git_repo: Path) -> None:
    """Files have correct status indicators."""
    (tmp_git_repo / "initial.txt").write_text("modified\n")
    (tmp_git_repo / "brand_new.py").write_text("new\n")
    git(tmp_git_repo, "add", "brand_new.py")  # stage so git diff HEAD sees it

    files = await _diff(tmp_git_repo)
    by_path = {diff_file.path: diff_file for diff_file in files}

    assert by_path["initial.txt"].status == FileStatus.MODIFIED
    assert by_path["brand_new.py"].status == FileStatus.ADDED


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

    assert by_path["logo.png"].unshown is Unshown.BINARY
    assert by_path["logo.png"].hunks == []


async def test_text_file_is_not_marked_as_binary(tmp_git_repo: Path) -> None:
    """A regular text change is not mistaken for binary."""
    (tmp_git_repo / "initial.txt").write_text("changed\n")

    files = await _diff(tmp_git_repo)
    by_path = {diff_file.path: diff_file for diff_file in files}

    assert by_path["initial.txt"].unshown is None


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
    assert by_path["x b/y.bin"].unshown is Unshown.BINARY


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
        # A diff tool of the reader's own, which must not stand in for git's format
        ("diff.external", "false"),
        ("core.quotePath", "false"),
    ],
)
async def test_the_readers_git_settings_do_not_change_what_is_shown(
    tmp_git_repo: Path, setting: str, value: str
) -> None:
    """A file added, one changed, one deleted and one named outside plain ASCII: each path is read from its own side.

    A deleted file is named only on the side before the change, so a prefix
    of the reader's there would be read as part of its path.
    """
    (tmp_git_repo / "gone.txt").write_text("gone\n")
    git(tmp_git_repo, "add", "gone.txt")
    git(tmp_git_repo, "commit", "-m", "a file to delete")
    (tmp_git_repo / "gone.txt").unlink()
    (tmp_git_repo / "a").mkdir()
    (tmp_git_repo / "a" / "inside.py").write_text("x = 1\n")
    (tmp_git_repo / "заметки.md").write_text("привет\n")
    (tmp_git_repo / "initial.txt").write_text("changed\n")
    git(tmp_git_repo, "config", setting, value)

    files = await _diff(tmp_git_repo)

    assert {diff_file.path for diff_file in files} == {"a/inside.py", "gone.txt", "initial.txt", "заметки.md"}
    assert all(diff_file.hunks for diff_file in files)


async def test_a_file_too_large_to_read_is_shown_without_its_lines(tmp_git_repo: Path) -> None:
    """A 50 MB log took a review half a minute and a gigabyte to show, and nobody reads one line by line."""
    lines = LARGEST_FILE_SHOWN_BYTES // len(LOG_LINE) + 1
    (tmp_git_repo / "generated.log").write_text(f"{LOG_LINE}\n" * lines)

    [shown] = await _diff(tmp_git_repo)

    assert shown.path == "generated.log"
    assert shown.unshown is Unshown.TOO_LARGE, "said too large, not binary: it is text, only long"
    assert shown.hunks == []


async def test_a_file_too_large_in_the_base_is_said_too_large_once_deleted(tmp_git_repo: Path) -> None:
    """Its size is the base's: git reads neither side of a file over the limit on either."""
    lines = LARGEST_FILE_SHOWN_BYTES // len(LOG_LINE) + 1
    (tmp_git_repo / "generated.log").write_text(f"{LOG_LINE}\n" * lines)
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "a long log")
    (tmp_git_repo / "generated.log").unlink()

    [shown] = await _diff(tmp_git_repo)

    assert (shown.status, shown.unshown) == (FileStatus.DELETED, Unshown.TOO_LARGE)


async def test_a_file_over_the_limit_whose_name_holds_a_line_break_is_still_shown(tmp_git_repo: Path) -> None:
    """Git is asked the sizes a name to a line, and such a name cannot be one: it stays as git said it, and the rest go on."""
    lines = LARGEST_FILE_SHOWN_BYTES // len(LOG_LINE) + 1
    (tmp_git_repo / "two\nlines.log").write_text(f"{LOG_LINE}\n" * lines)
    (tmp_git_repo / "generated.log").write_text(f"{LOG_LINE}\n" * lines)

    files = await _diff(tmp_git_repo)

    assert {diff_file.path: diff_file.unshown for diff_file in files} == {
        "generated.log": Unshown.TOO_LARGE,
        "two\nlines.log": Unshown.BINARY,
    }


async def test_a_binary_file_under_the_limit_beside_one_over_it_is_still_binary(tmp_git_repo: Path) -> None:
    """Each file is measured for itself."""
    lines = LARGEST_FILE_SHOWN_BYTES // len(LOG_LINE) + 1
    (tmp_git_repo / "generated.log").write_text(f"{LOG_LINE}\n" * lines)
    (tmp_git_repo / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x01\x02\x03")

    files = await _diff(tmp_git_repo)

    assert {diff_file.path: diff_file.unshown for diff_file in files} == {
        "generated.log": Unshown.TOO_LARGE,
        "logo.png": Unshown.BINARY,
    }


async def test_the_server_goes_on_answering_while_a_large_diff_is_read() -> None:
    """Read on the event loop, a diff of many files kept every page and agent waiting until it was done."""
    reading = asyncio.ensure_future(read_diff(StagingHeldStill(_large_change()), base=HEAD, ignore_whitespace=False))
    turns = 0
    while not reading.done():
        # A turn of the loop, as any socket the server holds is answered in
        await asyncio.sleep(0)
        turns += 1

    assert len(await reading) == FILES_IN_A_LARGE_DIFF
    assert turns > 1, "the loop came back to nothing else until the whole diff was read"


async def test_a_reader_who_refuses_unsafe_line_endings_can_still_open_a_review(tmp_git_repo: Path) -> None:
    """Git refuses to stage a CRLF file it would convert under core.safecrlf; the review's own index is no one's to guard."""
    git(tmp_git_repo, "config", "core.autocrlf", "input")
    git(tmp_git_repo, "config", "core.safecrlf", "true")
    (tmp_git_repo / "install.bat").write_bytes(b"@echo off\r\necho hi\r\n")

    files = await _diff(tmp_git_repo)

    assert [diff_file.path for diff_file in files] == ["install.bat"]

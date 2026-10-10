"""Functional tests for reading text files for review.

These test user-facing behavior: can a text file be loaded, reviewed,
and commented on — not the internal data structures used to represent it.
"""

from pathlib import Path

import pytest

from claude_review.services.text_files import read_text_files
from claude_review.services.unreadable_content import UnreadableContentError
from claude_review.services.whole_file import FIRST_LINE, whole_file

# Bytes no UTF-8 text starts with, as an image or a compiled file does
NOT_UTF8 = b"\x89PNG\r\n\x1a\n\xff\xfe"


def test_a_file_read_whole_starts_both_sides_of_its_hunk_at_its_first_line() -> None:
    """Its old side has no lines, and starts where they would, as any side with none does."""
    [hunk] = whole_file("plan.md", "Step 1\n").hunks

    assert (hunk.old_start, hunk.new_start) == (FIRST_LINE, FIRST_LINE)


class TestReadFiles:
    async def test_file_content_is_preserved_line_by_line(self, tmp_path: Path) -> None:
        """Every line of the original file is present and in order."""
        text_file = tmp_path / "plan.md"
        original = "# Title\n\nStep 1\nStep 2\n"
        text_file.write_text(original)

        result = await read_text_files([text_file], named_from=tmp_path)
        content = [line.content for line in result[0].hunks[0].lines]

        assert content == ["# Title", "", "Step 1", "Step 2"]

    async def test_every_line_has_a_commentable_line_number(self, tmp_path: Path) -> None:
        """Each line gets a sequential line number starting at 1."""
        text_file = tmp_path / "doc.md"
        text_file.write_text("first\nsecond\nthird\n")

        result = await read_text_files([text_file], named_from=tmp_path)
        line_numbers = [line.new_number for line in result[0].hunks[0].lines]

        assert line_numbers == [1, 2, 3]

    async def test_multiple_files_are_independently_reviewable(self, tmp_path: Path) -> None:
        """Each file becomes a separate reviewable entry, preserving order."""
        (tmp_path / "alpha.md").write_text("alpha\n")
        (tmp_path / "beta.md").write_text("beta\n")

        result = await read_text_files([tmp_path / "alpha.md", tmp_path / "beta.md"], named_from=tmp_path)

        assert [file.hunks[0].lines[0].content for file in result] == ["alpha", "beta"]

    async def test_empty_files_are_excluded(self, tmp_path: Path) -> None:
        """Empty files have nothing to review, so they are skipped."""
        (tmp_path / "empty.md").write_text("")
        (tmp_path / "content.md").write_text("hello\n")

        result = await read_text_files([tmp_path / "empty.md", tmp_path / "content.md"], named_from=tmp_path)

        assert len(result) == 1
        assert "content.md" in result[0].path

    async def test_missing_file_is_reported(self, tmp_path: Path) -> None:
        """A clear error is raised when a file does not exist."""
        with pytest.raises(UnreadableContentError):
            await read_text_files([tmp_path / "nonexistent.md"], named_from=tmp_path)

    async def test_a_file_that_is_not_text_is_reported(self, tmp_path: Path) -> None:
        """An image or a build artefact handed over by mistake is said to be one, not a crash."""
        binary = tmp_path / "image.png"
        binary.write_bytes(NOT_UTF8)

        with pytest.raises(UnreadableContentError, match=binary.name):
            await read_text_files([binary], named_from=tmp_path)

    async def test_trailing_newline_does_not_create_phantom_line(self, tmp_path: Path) -> None:
        """Files ending with \\n don't get an extra empty line."""
        text_file = tmp_path / "doc.md"
        text_file.write_text("line one\nline two\n")

        result = await read_text_files([text_file], named_from=tmp_path)

        assert [line.content for line in result[0].hunks[0].lines] == ["line one", "line two"]

    async def test_file_without_trailing_newline(self, tmp_path: Path) -> None:
        """Files not ending with \\n are handled identically."""
        text_file = tmp_path / "doc.md"
        text_file.write_text("line one\nline two")

        result = await read_text_files([text_file], named_from=tmp_path)

        assert [line.content for line in result[0].hunks[0].lines] == ["line one", "line two"]


async def test_a_file_under_the_directory_it_is_named_from_reads_relatively(tmp_path: Path) -> None:
    """ "docs/plan.md" is what the reader calls it, not its full path."""
    (tmp_path / "docs").mkdir()
    plan = tmp_path / "docs" / "plan.md"
    plan.write_text("# Plan\n")

    files = await read_text_files([plan], named_from=tmp_path)

    assert files[0].path == "docs/plan.md"


async def test_a_file_outside_the_directory_it_is_named_from_keeps_its_full_path(tmp_path: Path) -> None:
    """Shortening it to "../../elsewhere.md" would say less, not more."""
    outside = tmp_path / "elsewhere.md"
    outside.write_text("content\n")
    work = tmp_path / "work"
    work.mkdir()

    files = await read_text_files([outside], named_from=work)

    assert files[0].path == str(outside)

"""Functional tests for TextFileService.

These test user-facing behavior: can a text file be loaded, reviewed,
and commented on — not the internal data structures used to represent it.
"""

from pathlib import Path

import pytest

from claude_review.services.text_file_service import TextFileService
from claude_review.services.unreadable_content import UnreadableContentError

# Bytes no UTF-8 text starts with, as an image or a compiled file does
NOT_UTF8 = b"\x89PNG\r\n\x1a\n\xff\xfe"


@pytest.fixture
def service() -> TextFileService:
    return TextFileService()


class TestReadFiles:
    def test_file_content_is_preserved_line_by_line(self, service: TextFileService, tmp_path: Path) -> None:
        """Every line of the original file is present and in order."""
        text_file = tmp_path / "plan.md"
        original = "# Title\n\nStep 1\nStep 2\n"
        text_file.write_text(original)

        result = service.read_files([text_file])
        content = [line.content for line in result[0].hunks[0].lines]

        assert content == ["# Title", "", "Step 1", "Step 2"]

    def test_every_line_has_a_commentable_line_number(self, service: TextFileService, tmp_path: Path) -> None:
        """Each line gets a sequential line number starting at 1."""
        text_file = tmp_path / "doc.md"
        text_file.write_text("first\nsecond\nthird\n")

        result = service.read_files([text_file])
        line_numbers = [line.new_number for line in result[0].hunks[0].lines]

        assert line_numbers == [1, 2, 3]

    def test_multiple_files_are_independently_reviewable(self, service: TextFileService, tmp_path: Path) -> None:
        """Each file becomes a separate reviewable entry, preserving order."""
        (tmp_path / "alpha.md").write_text("alpha\n")
        (tmp_path / "beta.md").write_text("beta\n")

        result = service.read_files([tmp_path / "alpha.md", tmp_path / "beta.md"])

        assert len(result) == 2
        assert result[0].hunks[0].lines[0].content == "alpha"
        assert result[1].hunks[0].lines[0].content == "beta"

    def test_file_path_is_absolute_for_unambiguous_comments(self, service: TextFileService, tmp_path: Path) -> None:
        """Comments reference the resolved absolute path."""
        text_file = tmp_path / "sub" / "plan.md"
        text_file.parent.mkdir()
        text_file.write_text("content\n")

        result = service.read_files([text_file])

        assert result[0].path == str(text_file.resolve())

    def test_empty_files_are_excluded(self, service: TextFileService, tmp_path: Path) -> None:
        """Empty files have nothing to review, so they are skipped."""
        (tmp_path / "empty.md").write_text("")
        (tmp_path / "content.md").write_text("hello\n")

        result = service.read_files([tmp_path / "empty.md", tmp_path / "content.md"])

        assert len(result) == 1
        assert "content.md" in result[0].path

    def test_missing_file_is_reported(self, service: TextFileService, tmp_path: Path) -> None:
        """A clear error is raised when a file does not exist."""
        with pytest.raises(UnreadableContentError):
            service.read_files([tmp_path / "nonexistent.md"])

    def test_a_file_that_is_not_text_is_reported(self, service: TextFileService, tmp_path: Path) -> None:
        """An image or a build artefact handed over by mistake is said to be one, not a crash."""
        binary = tmp_path / "image.png"
        binary.write_bytes(NOT_UTF8)

        with pytest.raises(UnreadableContentError, match=binary.name):
            service.read_files([binary])

    def test_duplicate_paths_are_loaded_once(self, service: TextFileService, tmp_path: Path) -> None:
        """Passing the same file twice does not create duplicate entries."""
        text_file = tmp_path / "plan.md"
        text_file.write_text("content\n")

        result = service.read_files([text_file, text_file])

        assert len(result) == 1

    def test_trailing_newline_does_not_create_phantom_line(self, service: TextFileService, tmp_path: Path) -> None:
        """Files ending with \\n don't get an extra empty line."""
        text_file = tmp_path / "doc.md"
        text_file.write_text("line one\nline two\n")

        result = service.read_files([text_file])

        assert len(result[0].hunks[0].lines) == 2

    def test_file_without_trailing_newline(self, service: TextFileService, tmp_path: Path) -> None:
        """Files not ending with \\n are handled identically."""
        text_file = tmp_path / "doc.md"
        text_file.write_text("line one\nline two")

        result = service.read_files([text_file])

        assert len(result[0].hunks[0].lines) == 2
        assert result[0].hunks[0].lines[-1].content == "line two"


def test_a_file_under_the_working_directory_is_named_relatively(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ "docs/plan.md" is what the reader calls it, not its full path."""
    (tmp_path / "docs").mkdir()
    plan = tmp_path / "docs" / "plan.md"
    plan.write_text("# Plan\n")
    monkeypatch.chdir(tmp_path)

    files = TextFileService().read_files([Path("docs/plan.md")])

    assert files[0].path == "docs/plan.md"


def test_a_file_outside_the_working_directory_keeps_its_full_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Shortening it to "../../elsewhere.md" would say less, not more."""
    outside = tmp_path / "elsewhere.md"
    outside.write_text("content\n")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)

    files = TextFileService().read_files([outside])

    assert files[0].path == str(outside.resolve())

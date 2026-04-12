"""Functional tests for TextFileService.

These test user-facing behavior: can a text file be loaded, reviewed,
and commented on — not the internal data structures used to represent it.
"""

from pathlib import Path

import pytest

from claude_review.services.text_file_service import TextFileService


@pytest.fixture
def service() -> TextFileService:
    return TextFileService()


class TestReadFiles:
    def test_file_content_is_preserved_line_by_line(self, service: TextFileService, tmp_path: Path) -> None:
        """Every line of the original file is present and in order."""
        f = tmp_path / "plan.md"
        original = "# Title\n\nStep 1\nStep 2\n"
        f.write_text(original)

        result = service.read_files([f])
        content = [line.content for line in result[0].hunks[0].lines]

        assert content == ["# Title", "", "Step 1", "Step 2"]

    def test_every_line_has_a_commentable_line_number(self, service: TextFileService, tmp_path: Path) -> None:
        """Each line gets a sequential line number starting at 1."""
        f = tmp_path / "doc.md"
        f.write_text("first\nsecond\nthird\n")

        result = service.read_files([f])
        line_numbers = [line.new_no for line in result[0].hunks[0].lines]

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
        f = tmp_path / "sub" / "plan.md"
        f.parent.mkdir()
        f.write_text("content\n")

        result = service.read_files([f])

        assert result[0].path == str(f.resolve())

    def test_empty_files_are_excluded(self, service: TextFileService, tmp_path: Path) -> None:
        """Empty files have nothing to review, so they are skipped."""
        (tmp_path / "empty.md").write_text("")
        (tmp_path / "content.md").write_text("hello\n")

        result = service.read_files([tmp_path / "empty.md", tmp_path / "content.md"])

        assert len(result) == 1
        assert "content.md" in result[0].path

    def test_missing_file_is_reported(self, service: TextFileService, tmp_path: Path) -> None:
        """A clear error is raised when a file does not exist."""
        with pytest.raises(FileNotFoundError):
            service.read_files([tmp_path / "nonexistent.md"])

    def test_duplicate_paths_are_loaded_once(self, service: TextFileService, tmp_path: Path) -> None:
        """Passing the same file twice does not create duplicate entries."""
        f = tmp_path / "plan.md"
        f.write_text("content\n")

        result = service.read_files([f, f])

        assert len(result) == 1

    def test_trailing_newline_does_not_create_phantom_line(self, service: TextFileService, tmp_path: Path) -> None:
        """Files ending with \\n don't get an extra empty line."""
        f = tmp_path / "doc.md"
        f.write_text("line one\nline two\n")

        result = service.read_files([f])

        assert len(result[0].hunks[0].lines) == 2

    def test_file_without_trailing_newline(self, service: TextFileService, tmp_path: Path) -> None:
        """Files not ending with \\n are handled identically."""
        f = tmp_path / "doc.md"
        f.write_text("line one\nline two")

        result = service.read_files([f])

        assert len(result[0].hunks[0].lines) == 2
        assert result[0].hunks[0].lines[-1].content == "line two"

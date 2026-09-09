"""Functional tests for reading a window of lines out of a file.

Expanding the context around a hunk means asking the server for lines the
diff did not include, so this is the one place the review server reads an
arbitrary path the browser named.
"""

from pathlib import Path

import pytest

from claude_review.domain.exceptions import FileWindowError
from claude_review.services.file_window_service import FileWindowService


@pytest.fixture
def service() -> FileWindowService:
    return FileWindowService()


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("".join(f"line {i}\n" for i in range(1, 21)))
    return tmp_path


def test_reads_the_requested_lines(service: FileWindowService, root: Path) -> None:
    """Lines are returned by their number in the file, counting from one."""
    window = service.read_window(root, "src/app.py", start=3, end=5)

    assert window.lines == ["line 3", "line 4", "line 5"]
    assert window.start == 3


def test_reports_how_long_the_file_is(service: FileWindowService, root: Path) -> None:
    """The caller needs the total to know how much is left below the last hunk."""
    window = service.read_window(root, "src/app.py", start=1, end=2)

    assert window.total == 20


def test_clamps_a_window_that_runs_past_the_end(service: FileWindowService, root: Path) -> None:
    window = service.read_window(root, "src/app.py", start=19, end=100)

    assert window.lines == ["line 19", "line 20"]


def test_refuses_a_path_outside_the_repository(service: FileWindowService, root: Path) -> None:
    """The browser names the path, so it must not be able to leave the tree."""
    (root.parent / "secret.txt").write_text("private\n")

    with pytest.raises(FileWindowError):
        service.read_window(root, "../secret.txt", start=1, end=1)


def test_refuses_an_absolute_path(service: FileWindowService, root: Path) -> None:
    with pytest.raises(FileWindowError):
        service.read_window(root, "/etc/passwd", start=1, end=1)


def test_refuses_a_symlink_that_leaves_the_repository(service: FileWindowService, root: Path) -> None:
    outside = root.parent / "outside.txt"
    outside.write_text("private\n")
    (root / "link.txt").symlink_to(outside)

    with pytest.raises(FileWindowError):
        service.read_window(root, "link.txt", start=1, end=1)


def test_reports_a_missing_file(service: FileWindowService, root: Path) -> None:
    with pytest.raises(FileWindowError):
        service.read_window(root, "src/gone.py", start=1, end=1)


def test_reports_a_file_that_is_not_text(service: FileWindowService, root: Path) -> None:
    (root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe")

    with pytest.raises(FileWindowError):
        service.read_window(root, "logo.png", start=1, end=1)


def test_refuses_a_start_line_below_one(service: FileWindowService, root: Path) -> None:
    with pytest.raises(FileWindowError):
        service.read_window(root, "src/app.py", start=0, end=3)

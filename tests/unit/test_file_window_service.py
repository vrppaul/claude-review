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


async def test_reads_the_requested_lines(service: FileWindowService, root: Path) -> None:
    """Lines are returned by their number in the file, counting from one."""
    window = await service.read_window(root, "src/app.py", start=3, end=5)

    assert window.lines == ["line 3", "line 4", "line 5"]
    assert window.start == 3


async def test_reports_how_long_the_file_is(service: FileWindowService, root: Path) -> None:
    """The caller needs the total to know how much is left below the last hunk."""
    window = await service.read_window(root, "src/app.py", start=1, end=2)

    assert window.total == 20


async def test_clamps_a_window_that_runs_past_the_end(service: FileWindowService, root: Path) -> None:
    window = await service.read_window(root, "src/app.py", start=19, end=100)

    assert window.lines == ["line 19", "line 20"]


async def test_refuses_a_path_outside_the_repository(service: FileWindowService, root: Path) -> None:
    """The browser names the path, so it must not be able to leave the tree."""
    (root.parent / "secret.txt").write_text("private\n")

    with pytest.raises(FileWindowError):
        await service.read_window(root, "../secret.txt", start=1, end=1)


async def test_refuses_an_absolute_path(service: FileWindowService, root: Path) -> None:
    with pytest.raises(FileWindowError):
        await service.read_window(root, "/etc/passwd", start=1, end=1)


async def test_refuses_a_symlink_that_leaves_the_repository(service: FileWindowService, root: Path) -> None:
    outside = root.parent / "outside.txt"
    outside.write_text("private\n")
    (root / "link.txt").symlink_to(outside)

    with pytest.raises(FileWindowError):
        await service.read_window(root, "link.txt", start=1, end=1)


async def test_reports_a_missing_file(service: FileWindowService, root: Path) -> None:
    with pytest.raises(FileWindowError):
        await service.read_window(root, "src/gone.py", start=1, end=1)


async def test_reports_a_file_that_is_not_text(service: FileWindowService, root: Path) -> None:
    (root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe")

    with pytest.raises(FileWindowError):
        await service.read_window(root, "logo.png", start=1, end=1)


async def test_refuses_a_start_line_below_one(service: FileWindowService, root: Path) -> None:
    with pytest.raises(FileWindowError):
        await service.read_window(root, "src/app.py", start=0, end=3)


async def test_only_files_in_the_review_can_be_read(service: FileWindowService, root: Path) -> None:
    """The UI never asks for anything else, and the review is not a way to read
    the rest of the repository."""
    (root / ".env").write_text("SECRET=hunter2\n")

    with pytest.raises(FileWindowError):
        await service.read_window(root, ".env", start=1, end=1, allowed=["src/app.py"])


async def test_a_file_in_the_review_is_served(service: FileWindowService, root: Path) -> None:
    window = await service.read_window(root, "src/app.py", start=1, end=2, allowed=["src/app.py"])

    assert window.lines == ["line 1", "line 2"]


async def test_a_path_with_a_null_byte_is_refused_not_crashed(service: FileWindowService, root: Path) -> None:
    with pytest.raises(FileWindowError):
        await service.read_window(root, "src/a\x00b.py", start=1, end=1)


async def test_a_file_too_large_to_expand_is_refused(service: FileWindowService, root: Path) -> None:
    """Reading one used to load the whole thing, stalling the server for seconds."""
    from claude_review.services.file_window_service import MAX_FILE_BYTES

    big = root / "generated.txt"
    big.write_bytes(b"x\n" * (MAX_FILE_BYTES // 2 + 10))

    with pytest.raises(FileWindowError):
        await service.read_window(root, "generated.txt", start=1, end=2)


async def test_an_error_does_not_name_the_server_s_own_paths(service: FileWindowService, root: Path) -> None:
    """The message goes to the browser, so it says what was asked for."""
    try:
        await service.read_window(root, "src/gone.py", start=1, end=1)
    except FileWindowError as e:
        assert str(root) not in str(e)
        assert "src/gone.py" in str(e)
    else:
        pytest.fail("expected the read to be refused")


async def test_reading_a_window_does_not_depend_on_the_file_size(service: FileWindowService, root: Path) -> None:
    """A window near the top of a long file costs the top of the file, not all of it."""
    long_file = root / "long.txt"
    long_file.write_text("".join(f"line {i}\n" for i in range(1, 200_001)))

    window = await service.read_window(root, "long.txt", start=2, end=4)

    assert window.lines == ["line 2", "line 3", "line 4"]
    assert window.total == 200_000

"""Functional tests for reading a window of lines out of a file.

Expanding the context around a hunk means asking the server for lines the
diff did not include, so this is the one place the review server reads an
arbitrary path the browser named.
"""

from pathlib import Path
from typing import override

import pytest

from claude_review.domain.exceptions import (
    FileNotInReviewError,
    FileUnreadableError,
    LineRangeError,
    PathOutsideRepositoryError,
)
from claude_review.domain.interfaces import TrackedPaths
from claude_review.services.file_window_service import MAX_FILE_BYTES, FileWindowService

# How many lines the reviewed source file holds, and the long one
SOURCE_LINES = 20
LONG_FILE_LINES = 200_000
# How a PNG starts: its signature, then the length and name of its first chunk
PNG_HEADER = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR"


class RepositoryThatTracks(TrackedPaths):
    """A repository that tracks the paths it is given and nothing else."""

    def __init__(self, tracked: set[str]) -> None:
        self._tracked = tracked

    @override
    async def is_tracked(self, root: Path, relative_path: str) -> bool:
        return relative_path in self._tracked


@pytest.fixture
def service() -> FileWindowService:
    return FileWindowService(RepositoryThatTracks({"docs/guide.md"}))


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "".join(f"line {line_number}\n" for line_number in range(1, SOURCE_LINES + 1))
    )
    return tmp_path


async def test_lines_are_read_by_their_number_in_the_file(service: FileWindowService, root: Path) -> None:
    """Lines are returned by their number in the file, counting from one."""
    first, last = 3, 5

    window = await service.read_window(root, "src/app.py", start=first, end=last, in_review=frozenset({"src/app.py"}))

    assert window.lines == ["line 3", "line 4", "line 5"]
    assert window.start == first


async def test_a_window_past_the_end_stops_at_the_last_line(service: FileWindowService, root: Path) -> None:
    window = await service.read_window(root, "src/app.py", start=19, end=100, in_review=frozenset({"src/app.py"}))

    assert window.lines == ["line 19", "line 20"]


async def test_a_path_outside_the_repository_is_refused(service: FileWindowService, root: Path) -> None:
    """The browser names the path, so it must not be able to leave the tree."""
    (root.parent / "secret.txt").write_text("private\n")

    with pytest.raises(PathOutsideRepositoryError):
        await service.read_window(root, "../secret.txt", start=1, end=1, in_review=frozenset({"../secret.txt"}))


async def test_an_absolute_path_is_refused(service: FileWindowService, root: Path) -> None:
    with pytest.raises(PathOutsideRepositoryError):
        await service.read_window(root, "/etc/passwd", start=1, end=1, in_review=frozenset({"/etc/passwd"}))


async def test_a_symlink_that_leaves_the_repository_is_refused(service: FileWindowService, root: Path) -> None:
    outside = root.parent / "outside.txt"
    outside.write_text("private\n")
    (root / "link.txt").symlink_to(outside)

    with pytest.raises(PathOutsideRepositoryError):
        await service.read_window(root, "link.txt", start=1, end=1, in_review=frozenset({"link.txt"}))


async def test_a_missing_file_is_refused(service: FileWindowService, root: Path) -> None:
    with pytest.raises(FileNotInReviewError):
        await service.read_window(root, "src/gone.py", start=1, end=1, in_review=frozenset({"src/gone.py"}))


async def test_a_file_that_is_not_text_is_refused(service: FileWindowService, root: Path) -> None:
    """Not text as git tells it: a NUL byte among the first it reads, as a PNG's header has."""
    (root / "logo.png").write_bytes(PNG_HEADER)

    with pytest.raises(FileUnreadableError):
        await service.read_window(root, "logo.png", start=1, end=1, in_review=frozenset({"logo.png"}))


async def test_a_lone_carriage_return_is_part_of_its_line_as_git_numbers_them(
    service: FileWindowService, root: Path
) -> None:
    """Read as a line break, it would shift every line below it, and the widened context would not be the file's."""
    (root / "old-mac.txt").write_bytes(b"one\rtwo\nthree\n")

    window = await service.read_window(root, "old-mac.txt", start=1, end=2, in_review=frozenset({"old-mac.txt"}))

    assert window.lines == ["one\rtwo", "three"]
    assert window.total == len(window.lines)


async def test_a_file_in_another_encoding_is_read_with_its_odd_characters_replaced(
    service: FileWindowService, root: Path
) -> None:
    """As the diff shows it: one file in another encoding costs its own odd characters, not being read at all."""
    (root / "legacy.txt").write_bytes("café\n".encode("latin-1"))

    window = await service.read_window(root, "legacy.txt", start=1, end=1, in_review=frozenset({"legacy.txt"}))

    assert window.lines == ["caf\N{REPLACEMENT CHARACTER}"]


async def test_a_link_in_the_review_is_not_widened_into_the_file_it_points_at(
    service: FileWindowService, root: Path
) -> None:
    """A tracked link to an ignored `.env`: its lines are the link's, never the secret's."""
    (root / ".env").write_text("TOKEN=hunter2\n")
    (root / "settings").symlink_to(".env")

    with pytest.raises(FileUnreadableError):
        await service.read_window(root, "settings", start=1, end=1, in_review=frozenset({"settings"}))


async def test_a_start_line_below_one_is_refused(service: FileWindowService, root: Path) -> None:
    with pytest.raises(LineRangeError):
        await service.read_window(root, "src/app.py", start=0, end=3, in_review=frozenset({"src/app.py"}))


async def test_lines_that_run_backwards_are_refused(service: FileWindowService, root: Path) -> None:
    with pytest.raises(LineRangeError):
        await service.read_window(root, "src/app.py", start=3, end=1, in_review=frozenset({"src/app.py"}))


async def test_only_files_in_the_review_can_be_read(service: FileWindowService, root: Path) -> None:
    """The UI never asks for anything else, and the review is not a way to read
    the rest of the repository."""
    (root / ".env").write_text("SECRET=hunter2\n")

    with pytest.raises(FileNotInReviewError):
        await service.read_window(root, ".env", start=1, end=1, in_review=frozenset({"src/app.py"}))


async def test_a_path_with_a_null_byte_is_refused_not_crashed(service: FileWindowService, root: Path) -> None:
    with pytest.raises(PathOutsideRepositoryError):
        await service.read_window(root, "src/a\x00b.py", start=1, end=1, in_review=frozenset({"src/a\x00b.py"}))


async def test_a_file_too_large_to_expand_is_refused(service: FileWindowService, root: Path) -> None:
    """Reading one used to load the whole thing, stalling the server for seconds."""
    big = root / "generated.txt"
    big.write_bytes(b"x\n" * (MAX_FILE_BYTES // 2 + 10))

    with pytest.raises(FileUnreadableError):
        await service.read_window(root, "generated.txt", start=1, end=2, in_review=frozenset({"generated.txt"}))


async def test_an_error_does_not_name_the_server_s_own_paths(service: FileWindowService, root: Path) -> None:
    """The message goes to the browser, so it says what was asked for."""
    with pytest.raises(FileNotInReviewError) as refused:
        await service.read_window(root, "src/gone.py", start=1, end=1, in_review=frozenset({"src/gone.py"}))

    assert str(root) not in str(refused.value)
    assert "src/gone.py" in str(refused.value)


async def test_a_window_near_the_top_of_a_long_file_still_says_how_long_it_is(
    service: FileWindowService, root: Path
) -> None:
    """The reader is told how far the file goes, so the gap below a hunk can say so."""
    long_file = root / "long.txt"
    long_file.write_text("".join(f"line {line_number}\n" for line_number in range(1, LONG_FILE_LINES + 1)))

    window = await service.read_window(root, "long.txt", start=2, end=4, in_review=frozenset({"long.txt"}))

    assert window.lines == ["line 2", "line 3", "line 4"]
    assert window.total == LONG_FILE_LINES


async def test_a_tracked_file_another_base_shows_can_be_widened(service: FileWindowService, root: Path) -> None:
    """Read against a branch, the diff holds files the review's own diff does not."""
    (root / "docs").mkdir()
    (root / "docs" / "guide.md").write_text("one\ntwo\n")

    window = await service.read_window(root, "docs/guide.md", start=1, end=2, in_review=frozenset({"src/app.py"}))

    assert window.lines == ["one", "two"]

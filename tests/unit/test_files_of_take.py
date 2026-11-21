"""Functional requirement tests for reading a file of the take on screen: whole, or the lines a hunk left out.

Whatever is read of a take is read from the tree it was written down as,
never the disk: a test hands the reading a tree held in memory.
"""

from pathlib import Path

import pytest

from claude_review.domain.exceptions import FileNotInReviewError, FileUnreadableError, LineRangeError
from claude_review.domain.models import (
    MAX_WINDOW_LINES,
    NO_HUNK_HEADER,
    DiffHunk,
    DiffLine,
    FileOfTake,
    FilesRead,
    FileWindow,
    LineType,
    Unshown,
    UnshownFileOfTake,
)
from claude_review.services.files_of_take import FilesOfTake
from tests.without_git import TreesHeld

ROOT = Path("/repository-read-from-trees")
TAKE = "take-tree"

# How many lines the take's app holds, and one more line than a read of a file hands back
APP_LINES = 20
LONGER_THAN_A_READ = MAX_WINDOW_LINES + 1

TAKE_FILES = FilesRead(
    contents={
        "src/flags.py": b"def shown() -> bool:\r\n    return True\n",
        "src/app.py": "".join(f"line {number}\n" for number in range(1, APP_LINES + 1)).encode(),
        "old-mac.txt": b"one\rtwo\nthree\n",
        "legacy.txt": "caf\N{LATIN SMALL LETTER E WITH ACUTE}\n".encode("latin-1"),
        "long.txt": b"a line\n" * LONGER_THAN_A_READ,
        "logo.png": b"\x89PNG\r\n\x1a\n\0\0\0",
    },
    too_large=frozenset({"dump.log"}),
)


def files_of_take() -> FilesOfTake:
    return FilesOfTake(TreesHeld({TAKE: TAKE_FILES}), ROOT)


async def test_a_file_of_the_take_is_read_whole_every_line_on_the_new_side_as_git_numbers_it() -> None:
    """A carriage return is part of its line, as git keeps it."""
    read = await files_of_take().file(TAKE, "src/flags.py")

    assert read == FileOfTake(
        path="src/flags.py",
        hunk=DiffHunk(
            header=NO_HUNK_HEADER,
            old_start=1,
            new_start=1,
            lines=[
                DiffLine(kind=LineType.CONTEXT, old_number=None, new_number=1, content="def shown() -> bool:\r"),
                DiffLine(kind=LineType.CONTEXT, old_number=None, new_number=2, content="    return True"),
            ],
        ),
    )


async def test_a_path_the_take_holds_no_file_at_is_refused_as_not_there() -> None:
    with pytest.raises(FileNotInReviewError, match="src/gone.py"):
        await files_of_take().file(TAKE, "src/gone.py")


async def test_of_the_files_a_thread_names_only_those_the_review_reads_line_by_line_are_read_whole() -> None:
    """A thread on a binary file, one too large, or one the take lacks has no lines to follow or quote."""
    read = await files_of_take().text_files(TAKE, ["src/flags.py", "logo.png", "dump.log", "src/gone.py"])

    assert [file.path for file in read] == ["src/flags.py"]


@pytest.mark.parametrize(
    ("path", "unshown"),
    [("logo.png", Unshown.BINARY), ("dump.log", Unshown.TOO_LARGE)],
    ids=["not-text", "larger-than-the-review-reads"],
)
async def test_a_file_the_review_does_not_read_line_by_line_is_opened_with_no_lines_and_says_why(
    path: str, unshown: Unshown
) -> None:
    opened = await files_of_take().file(TAKE, path)

    assert opened == UnshownFileOfTake(path=path, unshown=unshown)


async def test_lines_a_hunk_left_out_are_read_by_their_number_in_the_file_which_says_how_long_it_is() -> None:
    window = await files_of_take().window(TAKE, "src/app.py", start=3, end=5)

    assert window == FileWindow(start=3, lines=["line 3", "line 4", "line 5"], total=APP_LINES)


async def test_a_window_past_the_end_of_the_file_stops_at_its_last_line() -> None:
    """Whoever asks cannot know how long the file is before asking."""
    window = await files_of_take().window(TAKE, "src/app.py", start=19, end=100)

    assert window.lines == ["line 19", "line 20"]


async def test_a_window_holds_no_more_lines_than_one_read_hands_back() -> None:
    window = await files_of_take().window(TAKE, "long.txt", start=1, end=LONGER_THAN_A_READ)

    assert (len(window.lines), window.total) == (MAX_WINDOW_LINES, LONGER_THAN_A_READ)


async def test_a_lone_carriage_return_is_part_of_its_line_in_a_window_as_git_numbers_them() -> None:
    """Read as a line break, it would shift every line below it, and the widened context would not be the file's."""
    window = await files_of_take().window(TAKE, "old-mac.txt", start=1, end=2)

    assert window == FileWindow(start=1, lines=["one\rtwo", "three"], total=2)


async def test_a_window_of_a_file_in_another_encoding_is_read_with_its_odd_characters_replaced() -> None:
    """As the diff shows it: one file in another encoding costs its own odd characters, not being read at all."""
    window = await files_of_take().window(TAKE, "legacy.txt", start=1, end=1)

    assert window.lines == ["caf\N{REPLACEMENT CHARACTER}"]


@pytest.mark.parametrize(("start", "end"), [(0, 3), (3, 1)], ids=["below-the-first-line", "backwards"])
async def test_lines_no_file_could_have_are_refused(start: int, end: int) -> None:
    with pytest.raises(LineRangeError):
        await files_of_take().window(TAKE, "src/app.py", start=start, end=end)


async def test_a_window_of_a_path_the_take_holds_no_file_at_is_refused_as_not_there() -> None:
    with pytest.raises(FileNotInReviewError, match="src/gone.py"):
        await files_of_take().window(TAKE, "src/gone.py", start=1, end=1)


@pytest.mark.parametrize("path", ["logo.png", "dump.log"], ids=["not-text", "larger-than-the-review-reads"])
async def test_a_file_the_review_reads_no_lines_of_has_none_to_widen(path: str) -> None:
    with pytest.raises(FileUnreadableError, match=path):
        await files_of_take().window(TAKE, path, start=1, end=1)

"""Functional requirement tests for reading a file of the take on screen whole.

A file the change did not touch is read from the tree the take was written
down as, never the disk: a test hands the reading a tree held in memory.
"""

from pathlib import Path

import pytest

from claude_review.domain.exceptions import FileNotInReviewError
from claude_review.domain.models import (
    NO_HUNK_HEADER,
    DiffHunk,
    DiffLine,
    FileOfTake,
    FilesRead,
    LineType,
    Unshown,
    UnshownFileOfTake,
)
from claude_review.services.files_of_take import FilesOfTake
from tests.without_git import TreesHeld

ROOT = Path("/repository-read-from-trees")
TAKE = "take-tree"

TAKE_FILES = FilesRead(
    contents={
        "src/flags.py": b"def shown() -> bool:\r\n    return True\n",
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

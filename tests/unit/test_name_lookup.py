"""Functional requirement tests for looking a name up in the take on screen.

The lookup reads the trees git wrote down, never the disk: a test hands it
trees held in memory, the take's and the base's, each a file at a path.
"""

from pathlib import Path
from typing import override

import pytest

from claude_review.domain.code_names import CodePlace, DefinitionKind, FoundAs, NameFound, NamePlace
from claude_review.domain.exceptions import FileNotInReviewError
from claude_review.domain.interfaces import TreesRead
from claude_review.domain.models import DiffFile, DiffHunk, FileStatus, LineSide
from claude_review.services.code_names.lookup import NameLookup
from tests.helpers import HUNK_HEADER, added_line, context_line, diff_file, removed_line

ROOT = Path("/repository-read-from-trees")
TAKE = "take-tree"
BASE = "base-commit"

TAKE_FILES = {
    "src/flags.py": b"def shown() -> bool:\n    return True\n",
    "src/pane.py": b"from src.flags import shown\n# what is shown\nvisible = shown()\n",
}
BASE_FILES = {
    "src/visible.py": b"def shown() -> bool:\n    return False\n",
}
# The take's own diff: the definition moved from src/visible.py, and the use in src/pane.py written by the change
TAKE_DIFF = [
    diff_file(
        "src/pane.py",
        [
            context_line(1, 1, "from src.flags import shown"),
            context_line(2, 2, "# what is shown"),
            added_line(3, "visible = shown()"),
        ],
    ),
    DiffFile(
        path="src/flags.py",
        old_path="src/visible.py",
        status=FileStatus.RENAMED,
        hunks=[
            DiffHunk(
                header=HUNK_HEADER,
                old_start=1,
                new_start=1,
                lines=[
                    removed_line(1, "def shown() -> bool:"),
                    removed_line(2, "    return False"),
                    added_line(1, "def shown() -> bool:"),
                    added_line(2, "    return True"),
                ],
            )
        ],
    ),
]


class TreesHeld(TreesRead):
    """Trees held in memory, each a file at a path; every file of a tree is said to hold any word."""

    def __init__(self, trees: dict[str, dict[str, bytes]]) -> None:
        self._trees = trees

    @override
    async def paths_holding(self, root: Path, tree: str, word: str) -> list[str]:
        return list(self._trees[tree])

    @override
    async def files_of(self, root: Path, tree: str, paths: list[str]) -> dict[str, bytes]:
        held = self._trees[tree]
        return {path: held[path] for path in held.keys() & set(paths)}


def lookup() -> NameLookup:
    return NameLookup(TreesHeld({TAKE: TAKE_FILES, BASE: BASE_FILES}), ROOT)


async def test_a_name_is_found_in_every_file_of_the_take_the_uses_the_change_wrote_said_so() -> None:
    found = await lookup().name_at(
        CodePlace(path="src/pane.py", side=LineSide.NEW, line=3, column=11), tree=TAKE, base=BASE, files=TAKE_DIFF
    )

    assert found == NameFound(
        name="shown",
        places=[
            NamePlace(
                path="src/flags.py",
                line=1,
                column=4,
                text="def shown() -> bool:",
                defined_as=DefinitionKind.FUNCTION,
                inside=None,
                added=True,
                found_as=FoundAs.NAME,
            ),
            NamePlace(
                path="src/pane.py",
                line=1,
                column=22,
                text="from src.flags import shown",
                defined_as=None,
                inside=None,
                added=False,
                found_as=FoundAs.NAME,
            ),
            NamePlace(
                path="src/pane.py",
                line=3,
                column=10,
                text="visible = shown()",
                defined_as=None,
                inside="visible",
                added=True,
                found_as=FoundAs.NAME,
            ),
        ],
    )


async def test_a_name_on_the_old_side_is_read_where_its_file_stood_and_looked_for_in_the_take() -> None:
    found = await lookup().name_at(
        CodePlace(path="src/flags.py", side=LineSide.OLD, line=1, column=5), tree=TAKE, base=BASE, files=TAKE_DIFF
    )

    assert (found.name, [place.path for place in found.places]) == (
        "shown",
        ["src/flags.py", "src/pane.py", "src/pane.py"],
    )


@pytest.mark.parametrize(
    ("place", "name", "lines"),
    [
        (CodePlace(path="src/pane.py", side=LineSide.NEW, line=2, column=12), "shown", [1, 1, 3]),
        (CodePlace(path="src/flags.py", side=LineSide.NEW, line=2, column=6), "return", []),
    ],
    ids=["a-comment-word-a-function-is-called-by", "a-word-nothing-is-called-by"],
)
async def test_a_word_is_looked_up_wherever_it_stands_and_one_nothing_is_called_by_has_no_place(
    place: CodePlace, name: str, lines: list[int]
) -> None:
    found = await lookup().name_at(place, tree=TAKE, base=BASE, files=TAKE_DIFF)

    assert (found.name, [found_place.line for found_place in found.places]) == (name, lines)


@pytest.mark.parametrize(
    "place",
    [
        CodePlace(path="src/gone.py", side=LineSide.NEW, line=1, column=0),
        CodePlace(path="src/pane.py", side=LineSide.OLD, line=1, column=0),
    ],
    ids=["not-in-the-take", "not-in-the-base"],
)
async def test_a_place_in_a_file_the_side_has_none_of_is_refused(place: CodePlace) -> None:
    with pytest.raises(FileNotInReviewError):
        await lookup().name_at(place, tree=TAKE, base=BASE, files=TAKE_DIFF)

"""Functional requirement tests for the names a change touched, file by file, judged against the review's base.

The files are read from the trees git wrote down, never the disk: a test
hands the take's tree and the base's, each held in memory as a file at a
path, and the take's own diff, whose hunks say which lines the change added
and which it removed.
"""

from pathlib import Path

import pytest

from claude_review.domain.code_names import DefinitionKind, FileNamesTouched, LinesOnSide, NameChange, TouchedName
from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FilesRead, FileStatus, LineSide, Unshown
from claude_review.services.code_names import reading
from claude_review.services.code_names.outlines import Outlines
from claude_review.services.code_names.touched import read_names_touched
from tests.helpers import HUNK_HEADER, added_line, context_line, diff_file, removed_line
from tests.without_git import TreesHeld

ROOT = Path("/repository-read-from-trees")
TAKE = "take-tree"
BASE = "base-commit"
PATH = "src/pane.py"

FIRST_GONE_LAST = b"def first():\n    pass\n\n\ndef gone():\n    pass\n\n\ndef last():\n    pass\n"
FIRST_LAST = b"def first():\n    pass\n\n\ndef last():\n    pass\n"

# A function holding a run of comment lines Python's grammar reads in time that grows with its square, the run
# the change removed, and how long the test lets one file's parse take, short so the test stays cheap
PADDING_LINES = 3000
SLOW_TO_PARSE = b"def big():\n" + b"    # pad\n" * PADDING_LINES + b"    pass\n"
SHORT_PARSE_SECONDS = 0.01


def trees(take: dict[str, bytes], base: dict[str, bytes]) -> TreesHeld:
    return TreesHeld(
        {
            TAKE: FilesRead(contents=take, too_large=frozenset()),
            BASE: FilesRead(contents=base, too_large=frozenset()),
        }
    )


@pytest.mark.parametrize(
    ("base", "take", "lines", "touched"),
    [
        (
            b"def first(limit):\n    return limit\n",
            b"def first(limit, floor):\n    return limit\n",
            [
                removed_line(1, "def first(limit):"),
                added_line(1, "def first(limit, floor):"),
                context_line(2, 2, "    return limit"),
            ],
            [
                TouchedName(
                    name="first",
                    defined_as=DefinitionKind.FUNCTION,
                    change=NameChange.MODIFIED,
                    line=1,
                    column=4,
                    stands_on=[
                        LinesOnSide(side=LineSide.NEW, first=1, last=2),
                        LinesOnSide(side=LineSide.OLD, first=1, last=2),
                    ],
                )
            ],
        ),
        (
            b"def first():\n    run()\n    return 1\n",
            b"def first():\n    run()\n",
            [context_line(1, 1, "def first():"), context_line(2, 2, "    run()"), removed_line(3, "    return 1")],
            [
                TouchedName(
                    name="first",
                    defined_as=DefinitionKind.FUNCTION,
                    change=NameChange.MODIFIED,
                    line=1,
                    column=4,
                    stands_on=[
                        LinesOnSide(side=LineSide.NEW, first=1, last=2),
                        LinesOnSide(side=LineSide.OLD, first=1, last=3),
                    ],
                )
            ],
        ),
        (
            FIRST_GONE_LAST,
            FIRST_LAST,
            [
                context_line(1, 1, "def first():"),
                context_line(2, 2, "    pass"),
                context_line(3, 3, ""),
                context_line(4, 4, ""),
                removed_line(5, "def gone():"),
                removed_line(6, "    pass"),
                removed_line(7, ""),
                removed_line(8, ""),
                context_line(9, 5, "def last():"),
                context_line(10, 6, "    pass"),
            ],
            [
                TouchedName(
                    name="gone",
                    defined_as=DefinitionKind.FUNCTION,
                    change=NameChange.REMOVED,
                    line=5,
                    column=4,
                    stands_on=[LinesOnSide(side=LineSide.OLD, first=5, last=6)],
                )
            ],
        ),
        (
            b"def first():\n    pass\n",
            b"def first():\n    pass\n\n\ndef second():\n    pass\n",
            [
                context_line(1, 1, "def first():"),
                context_line(2, 2, "    pass"),
                added_line(3, ""),
                added_line(4, ""),
                added_line(5, "def second():"),
                added_line(6, "    pass"),
            ],
            [
                TouchedName(
                    name="second",
                    defined_as=DefinitionKind.FUNCTION,
                    change=NameChange.ADDED,
                    line=5,
                    column=4,
                    stands_on=[LinesOnSide(side=LineSide.NEW, first=5, last=6)],
                )
            ],
        ),
        (
            b"def first():\n    pass\n",
            b"def renamed():\n    pass\n",
            [removed_line(1, "def first():"), added_line(1, "def renamed():"), context_line(2, 2, "    pass")],
            [
                TouchedName(
                    name="first",
                    defined_as=DefinitionKind.FUNCTION,
                    change=NameChange.REMOVED,
                    line=1,
                    column=4,
                    stands_on=[LinesOnSide(side=LineSide.OLD, first=1, last=2)],
                ),
                TouchedName(
                    name="renamed",
                    defined_as=DefinitionKind.FUNCTION,
                    change=NameChange.ADDED,
                    line=1,
                    column=4,
                    stands_on=[LinesOnSide(side=LineSide.NEW, first=1, last=2)],
                ),
            ],
        ),
        (
            b"def first():\n    pass\n",
            b"@cache\ndef first():\n    pass\n",
            [added_line(1, "@cache"), context_line(1, 2, "def first():"), context_line(2, 3, "    pass")],
            [
                TouchedName(
                    name="first",
                    defined_as=DefinitionKind.FUNCTION,
                    change=NameChange.MODIFIED,
                    line=2,
                    column=4,
                    stands_on=[
                        LinesOnSide(side=LineSide.NEW, first=1, last=3),
                        LinesOnSide(side=LineSide.OLD, first=1, last=2),
                    ],
                )
            ],
        ),
    ],
    ids=[
        "a-signature-rewritten-is-modified",
        "the-last-lines-removed-touch-it",
        "a-function-removed-whole-is-removed-on-the-lines-it-stood-on",
        "a-function-written-beside-is-added",
        "a-function-renamed-is-the-old-name-removed-and-the-new-added",
        "a-decorator-added-touches-its-function",
    ],
)
async def test_what_became_of_a_name_is_judged_against_the_base(
    base: bytes, take: bytes, lines: list[DiffLine], touched: list[TouchedName]
) -> None:
    names = await read_names_touched(
        Outlines(trees({PATH: take}, {PATH: base}), ROOT), tree=TAKE, base=BASE, files=[diff_file(PATH, lines)]
    )

    assert [name for file in names for name in file.names] == touched


@pytest.mark.parametrize(
    ("base", "take", "hunk", "met"),
    [
        (
            FIRST_GONE_LAST.replace(b"    pass\n", b"    return 1\n"),
            b"def added():\n    pass\n\n\ndef first():\n    return 1\n\n\ndef last():\n    return 2\n",
            DiffHunk(
                header=HUNK_HEADER,
                old_start=1,
                new_start=1,
                lines=[
                    added_line(1, "def added():"),
                    added_line(2, "    pass"),
                    added_line(3, ""),
                    added_line(4, ""),
                    context_line(1, 5, "def first():"),
                    context_line(2, 6, "    return 1"),
                    context_line(3, 7, ""),
                    context_line(4, 8, ""),
                    removed_line(5, "def gone():"),
                    removed_line(6, "    return 1"),
                    removed_line(7, ""),
                    removed_line(8, ""),
                    context_line(9, 9, "def last():"),
                    removed_line(10, "    return 1"),
                    added_line(10, "    return 2"),
                ],
            ),
            ["added", "gone", "last"],
        ),
        (
            b"def first():\n    pass\ndef gone():\n    return 1\n",
            b"def first():\n    pass\nclass Holder:\n    def gone():\n        return 1\n",
            DiffHunk(header=HUNK_HEADER, old_start=3, new_start=3, lines=[added_line(3, "class Holder:")]),
            ["Holder", "gone"],
        ),
    ],
    ids=["a-removed-name-stands-where-its-lines-were-removed", "a-name-on-a-line-no-hunk-shows-stands-where-it-is-now"],
)
async def test_the_names_of_a_file_stand_in_the_order_a_reader_meets_them_down_its_diff(
    base: bytes, take: bytes, hunk: DiffHunk, met: list[str]
) -> None:
    file = DiffFile(path=PATH, status=FileStatus.MODIFIED, hunks=[hunk])

    names = await read_names_touched(
        Outlines(trees({PATH: take}, {PATH: base}), ROOT), tree=TAKE, base=BASE, files=[file]
    )

    assert [name.name for file in names for name in file.names] == met


async def test_a_renamed_file_s_names_are_judged_against_the_file_it_moved_from() -> None:
    renamed = DiffFile(
        path="src/new.py",
        old_path="src/old.py",
        status=FileStatus.RENAMED,
        hunks=diff_file(
            "src/new.py",
            [context_line(1, 1, "def first():"), removed_line(2, "    pass"), added_line(2, "    return 1")],
        ).hunks,
    )

    names = await read_names_touched(
        Outlines(
            trees({"src/new.py": b"def first():\n    return 1\n"}, {"src/old.py": b"def first():\n    pass\n"}), ROOT
        ),
        tree=TAKE,
        base=BASE,
        files=[renamed],
    )

    assert names == [
        FileNamesTouched(
            path="src/new.py",
            names=[
                TouchedName(
                    name="first",
                    defined_as=DefinitionKind.FUNCTION,
                    change=NameChange.MODIFIED,
                    line=1,
                    column=4,
                    stands_on=[
                        LinesOnSide(side=LineSide.NEW, first=1, last=2),
                        LinesOnSide(side=LineSide.OLD, first=1, last=2),
                    ],
                )
            ],
        )
    ]


async def test_the_names_a_change_touched_are_said_file_by_file_in_the_order_of_its_diff() -> None:
    """A file the change added has every name added, and one it deleted every name removed; a file of no grammar,
    one added that is not text, one too large and one whose change touched no name say none, and are left out."""
    take_files = {
        PATH: b"def first():\n    return 2\n",
        "src/flags.py": b"def shown():\n    pass\n\n\ndef hidden():\n    pass\n",
        "src/notes.md": b"def shown\n",
        "src/logo.py": b"def shown():\n    pass\n\0\n",
        "src/limits.py": b"LIMIT = 2\n",
    }
    base_files = {
        PATH: b"def first():\n    return 1\n",
        "src/gone.py": b"def gone():\n    pass\n",
        "src/limits.py": b"LIMIT = 1\n",
    }
    held = TreesHeld(
        {
            TAKE: FilesRead(contents=take_files, too_large=frozenset({"src/large.py"})),
            BASE: FilesRead(contents=base_files, too_large=frozenset({"src/large.py"})),
        }
    )
    files = [
        diff_file(
            PATH, [context_line(1, 1, "def first():"), removed_line(2, "    return 1"), added_line(2, "    return 2")]
        ),
        diff_file(
            "src/flags.py",
            [
                added_line(1, "def shown():"),
                added_line(2, "    pass"),
                added_line(3, ""),
                added_line(4, ""),
                added_line(5, "def hidden():"),
                added_line(6, "    pass"),
            ],
            status=FileStatus.ADDED,
        ),
        diff_file("src/notes.md", [added_line(1, "def shown")], status=FileStatus.ADDED),
        DiffFile(path="src/logo.py", status=FileStatus.ADDED, hunks=[], unshown=Unshown.BINARY),
        diff_file("src/limits.py", [removed_line(1, "LIMIT = 1"), added_line(1, "LIMIT = 2")]),
        DiffFile(path="src/large.py", status=FileStatus.MODIFIED, hunks=[], unshown=Unshown.TOO_LARGE),
        diff_file("src/gone.py", [removed_line(1, "def gone():"), removed_line(2, "    pass")], FileStatus.DELETED),
    ]

    names = await read_names_touched(Outlines(held, ROOT), tree=TAKE, base=BASE, files=files)

    assert names == [
        FileNamesTouched(
            path=PATH,
            names=[
                TouchedName(
                    name="first",
                    defined_as=DefinitionKind.FUNCTION,
                    change=NameChange.MODIFIED,
                    line=1,
                    column=4,
                    stands_on=[
                        LinesOnSide(side=LineSide.NEW, first=1, last=2),
                        LinesOnSide(side=LineSide.OLD, first=1, last=2),
                    ],
                )
            ],
        ),
        FileNamesTouched(
            path="src/flags.py",
            names=[
                TouchedName(
                    name="shown",
                    defined_as=DefinitionKind.FUNCTION,
                    change=NameChange.ADDED,
                    line=1,
                    column=4,
                    stands_on=[LinesOnSide(side=LineSide.NEW, first=1, last=2)],
                ),
                TouchedName(
                    name="hidden",
                    defined_as=DefinitionKind.FUNCTION,
                    change=NameChange.ADDED,
                    line=5,
                    column=4,
                    stands_on=[LinesOnSide(side=LineSide.NEW, first=5, last=6)],
                ),
            ],
        ),
        FileNamesTouched(
            path="src/gone.py",
            names=[
                TouchedName(
                    name="gone",
                    defined_as=DefinitionKind.FUNCTION,
                    change=NameChange.REMOVED,
                    line=1,
                    column=4,
                    stands_on=[LinesOnSide(side=LineSide.OLD, first=1, last=2)],
                )
            ],
        ),
    ]


async def test_a_file_whose_base_could_not_be_read_in_time_says_no_names(monkeypatch: pytest.MonkeyPatch) -> None:
    """What became of its names cannot be judged: none is said added for the base outlining nothing."""
    monkeypatch.setattr(reading, "LONGEST_PARSE_SECONDS", SHORT_PARSE_SECONDS)
    lines = [
        context_line(1, 1, "def big():"),
        *[removed_line(number, "    # pad") for number in range(2, PADDING_LINES + 2)],
        context_line(PADDING_LINES + 2, 2, "    pass"),
    ]

    names = await read_names_touched(
        Outlines(trees({PATH: b"def big():\n    pass\n"}, {PATH: SLOW_TO_PARSE}), ROOT),
        tree=TAKE,
        base=BASE,
        files=[diff_file(PATH, lines)],
    )

    assert names == []

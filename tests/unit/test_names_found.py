"""Functional requirement tests for the names the tree's filter finds outside the change, in the take's tree.

A test hands the take's tree, held in memory as a file at a path, and the
names the change touched, which the tree lists already. Every file of a
tree held so holds any text: which names hold it is the review's to say.
"""

import asyncio
from pathlib import Path
from typing import override

import pytest

from claude_review.domain.code_names import (
    DefinitionKind,
    FileNamesTouched,
    LinesOnSide,
    NameChange,
    NameDefined,
    NamesFound,
    TouchedName,
)
from claude_review.domain.interfaces import GitError
from claude_review.domain.models import FilesRead, LineSide
from claude_review.services.code_names.found import read_names_found
from claude_review.services.code_names.outlines import Outlines
from tests.without_git import TreesHeld, held_object_id

ROOT = Path("/repository-read-from-trees")
TAKE = "take-tree"
LATER_TAKE = "later-take-tree"
TAKE_NUMBER = 3
# How long a content git reads takes where a test needs one read to end after another
READ_A_WHILE_SECONDS = 0.05

ATTEMPTS = b"class FailedRun:\n    def fail_now(self):\n        pass\n\n\ndef failed_attempts():\n    pass\n"
LOG = b"def note_failure():\n    pass\n\n\ndef is_failure():\n    pass\n\n\ndef fail_safe():\n    pass\n"


class BlobsCounted(TreesHeld):
    """Trees held in memory that count each content they are asked to read, and give way while reading, as git's
    process does."""

    def __init__(self, trees: dict[str, FilesRead]) -> None:
        super().__init__(trees)
        self.blobs_read_count = 0

    @override
    async def blobs_read(self, root: Path, object_ids: list[str]) -> list[bytes]:
        self.blobs_read_count += len(object_ids)
        await asyncio.sleep(0)
        return await super().blobs_read(root, object_ids)


class BlobsFailing(TreesHeld):
    """Trees held in memory where git fails at once to read one content, and reads any other a while later."""

    def __init__(self, trees: dict[str, FilesRead], *, failing: str) -> None:
        super().__init__(trees)
        self._failing = failing

    @override
    async def blobs_read(self, root: Path, object_ids: list[str]) -> list[bytes]:
        if self._failing in object_ids:
            msg = "git could not read the content"
            raise GitError(msg)
        await asyncio.sleep(READ_A_WHILE_SECONDS)
        return await super().blobs_read(root, object_ids)


def held_tree(tree: str, files: dict[str, bytes]) -> TreesHeld:
    return TreesHeld({tree: FilesRead(contents=files, too_large=frozenset())})


def defined(name: str, kind: DefinitionKind, path: str, line: int, column: int) -> NameDefined:
    return NameDefined(name=name, defined_as=kind, path=path, line=line, column=column)


async def test_the_names_found_hold_the_text_whatever_its_case_and_the_change_s_own_are_left_to_the_tree() -> None:
    """Only names standing at the top of a file, those starting with the text first; an untouched name of a file the
    change touched is outside it too, and a file of no grammar outlines none."""
    held = held_tree(TAKE, {"src/log.py": LOG, "src/attempts.py": ATTEMPTS, "docs/failures.md": b"# fail_safe\n"})
    touched = [
        FileNamesTouched(
            path="src/log.py",
            names=[
                TouchedName(
                    name="is_failure",
                    defined_as=DefinitionKind.FUNCTION,
                    change=NameChange.ADDED,
                    line=5,
                    column=4,
                    stands_on=[LinesOnSide(side=LineSide.NEW, first=5, last=6)],
                )
            ],
        )
    ]

    found = await read_names_found(Outlines(held, ROOT), text="FAIL", tree=TAKE, touched=touched)

    assert found == [
        defined("FailedRun", DefinitionKind.CLASS, "src/attempts.py", 1, 6),
        defined("failed_attempts", DefinitionKind.FUNCTION, "src/attempts.py", 6, 4),
        defined("fail_safe", DefinitionKind.FUNCTION, "src/log.py", 9, 4),
        defined("note_failure", DefinitionKind.FUNCTION, "src/log.py", 1, 4),
    ]


async def test_a_file_rewritten_in_a_later_take_says_the_names_it_holds_there() -> None:
    held = TreesHeld(
        {
            TAKE: FilesRead(contents={"src/attempts.py": ATTEMPTS}, too_large=frozenset()),
            LATER_TAKE: FilesRead(
                contents={"src/attempts.py": b"def fail_later():\n    pass\n"}, too_large=frozenset()
            ),
        }
    )
    outlines = Outlines(held, ROOT)

    await read_names_found(outlines, text="fail", tree=TAKE, touched=[])
    found_later = await read_names_found(outlines, text="fail", tree=LATER_TAKE, touched=[])

    assert found_later == [defined("fail_later", DefinitionKind.FUNCTION, "src/attempts.py", 1, 4)]


async def test_searches_asked_at_once_read_a_file_once() -> None:
    """As a reader typing asks again before the last answer: what one search reads, another one waits for."""
    held = BlobsCounted({TAKE: FilesRead(contents={"src/attempts.py": ATTEMPTS}, too_large=frozenset())})
    outlines = Outlines(held, ROOT)

    found = await asyncio.gather(
        read_names_found(outlines, text="fail", tree=TAKE, touched=[]),
        read_names_found(outlines, text="failed", tree=TAKE, touched=[]),
    )

    assert (held.blobs_read_count, [len(names) for names in found]) == (1, [2, 2])


async def test_a_file_git_fails_to_read_fails_the_search_as_git_failed_while_another_file_is_read_apart() -> None:
    held = BlobsFailing(
        {TAKE: FilesRead(contents={"src/attempts.py": ATTEMPTS, "src/log.py": LOG}, too_large=frozenset())},
        failing=held_object_id(LOG),
    )
    outlines = Outlines(held, ROOT)
    reading_attempts = asyncio.create_task(outlines.of_files(TAKE, ["src/attempts.py"]))
    await asyncio.sleep(0)

    with pytest.raises(GitError):
        await outlines.of_files(TAKE, ["src/attempts.py", "src/log.py"])
    await reading_attempts


def test_an_answer_lists_twenty_names_and_says_how_many_more_hold_the_text() -> None:
    found = [defined(f"fail_{number}", DefinitionKind.FUNCTION, "src/many.py", number, 4) for number in range(1, 26)]

    listing = NamesFound.listing(TAKE_NUMBER, found)

    assert listing == NamesFound(take=TAKE_NUMBER, names=found[:20], more=5)

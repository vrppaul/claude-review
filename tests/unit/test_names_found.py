"""Functional requirement tests for the names the tree's filter finds outside the change, in the take's tree.

A test hands the take's tree, held in memory as a file at a path, and the
names the change touched, which the tree lists already. Every file of a
tree held so holds any text: which names hold it is the review's to say.
"""

import asyncio
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import override

import pytest

from claude_review.domain.code_names import (
    DefinitionKind,
    FileNamesTouched,
    LinesOnSide,
    NameChange,
    NameDefined,
    TouchedName,
)
from claude_review.domain.interfaces import GitError
from claude_review.domain.models import FilesRead, LineSide
from claude_review.services.code_names import reading
from claude_review.services.code_names.found import FoundSoFar, read_names_found
from claude_review.services.code_names.outlines import NamesParsing, Outlines, SearchWaits
from tests.without_git import WORKERS_IN_TESTS, OutlinesHeld, TreesHeld, held_object_id, parsing_in_tests

ROOT = Path("/repository-read-from-trees")
TAKE = "take-tree"
LATER_TAKE = "later-take-tree"
# How long a content git reads takes where a test needs one read to end after another
READ_A_WHILE_SECONDS = 0.05
# How long a search waits where a test needs every file outlined: far past what outlining a few takes
EVERY_FILE_OUTLINED_WITHIN_SECONDS = 10.0
EVERY_FILE_OUTLINED = SearchWaits(
    first_seconds=EVERY_FILE_OUTLINED_WITHIN_SECONDS, again_seconds=EVERY_FILE_OUTLINED_WITHIN_SECONDS
)
# A first answer given at once, with whatever is outlined by then
AT_ONCE = SearchWaits(first_seconds=0, again_seconds=EVERY_FILE_OUTLINED_WITHIN_SECONDS)
# Files enough to fill several chunks of outlining
MANY_FILES = 200
# Names enough in each of two files that, of either, one answer lists fewer than all
NAMES_PAST_LISTED = 21

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


class TextSearched(TreesHeld):
    """Trees held in memory whose files hold a text only where it is written in them, whatever its case; each search
    of one counted."""

    def __init__(self, trees: dict[str, FilesRead]) -> None:
        super().__init__(trees)
        self.searches_count = 0

    @override
    async def paths_with_text(self, root: Path, tree: str, text: str) -> list[str]:
        self.searches_count += 1
        read = await self.files_of(root, tree, list((await self.blobs_in(root, tree)).paths))
        return [path for path, content in read.contents.items() if text.lower().encode() in content.lower()]


class TextSearchedSlowly(TextSearched):
    """Trees held in memory, each search of one counted, whose contents take a while to read."""

    @override
    async def blobs_read(self, root: Path, object_ids: list[str]) -> list[bytes]:
        await asyncio.sleep(READ_A_WHILE_SECONDS)
        return await super().blobs_read(root, object_ids)


class BlobsSlow(TreesHeld):
    """Trees held in memory whose contents take a while to read."""

    @override
    async def blobs_read(self, root: Path, object_ids: list[str]) -> list[bytes]:
        await asyncio.sleep(READ_A_WHILE_SECONDS)
        return await super().blobs_read(root, object_ids)


class ChunksRecorded(ThreadPoolExecutor):
    """Threads to outline in that note the paths of each chunk of files they are given, in the order given."""

    def __init__(self, *, max_workers: int) -> None:
        super().__init__(max_workers=max_workers)
        self.paths_given: list[list[str]] = []

    @override
    def submit[**Takes, Gives](
        self, fn: Callable[Takes, Gives], /, *args: Takes.args, **kwargs: Takes.kwargs
    ) -> Future[Gives]:
        [files] = args
        self.paths_given.append([file.path for file in files])
        return super().submit(fn, *args, **kwargs)


async def search(outlines: Outlines, text: str, tree: str) -> FoundSoFar:
    """The names found outside a change that touched none, every file outlined."""
    return await read_names_found(outlines, text=text, tree=tree, touched=[], waits=EVERY_FILE_OUTLINED)


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

    found = await read_names_found(
        Outlines(held, ROOT, parsing_in_tests()),
        text="FAIL",
        tree=TAKE,
        touched=touched,
        waits=EVERY_FILE_OUTLINED,
    )

    assert found == FoundSoFar(
        names=[
            defined("FailedRun", DefinitionKind.CLASS, "src/attempts.py", 1, 6),
            defined("failed_attempts", DefinitionKind.FUNCTION, "src/attempts.py", 6, 4),
            defined("fail_safe", DefinitionKind.FUNCTION, "src/log.py", 9, 4),
            defined("note_failure", DefinitionKind.FUNCTION, "src/log.py", 1, 4),
        ],
        more=0,
        complete=True,
    )


async def test_a_file_rewritten_in_a_later_take_says_the_names_it_holds_there() -> None:
    held = TreesHeld(
        {
            TAKE: FilesRead(contents={"src/attempts.py": ATTEMPTS}, too_large=frozenset()),
            LATER_TAKE: FilesRead(
                contents={"src/attempts.py": b"def fail_later():\n    pass\n"}, too_large=frozenset()
            ),
        }
    )
    outlines = Outlines(held, ROOT, parsing_in_tests())

    await search(outlines, "fail", TAKE)
    found_later = await search(outlines, "fail", LATER_TAKE)

    assert found_later.names == [defined("fail_later", DefinitionKind.FUNCTION, "src/attempts.py", 1, 4)]


async def test_searches_asked_at_once_read_a_file_once() -> None:
    """As a reader typing asks again before the last answer: what one search reads, another one waits for."""
    held = BlobsCounted({TAKE: FilesRead(contents={"src/attempts.py": ATTEMPTS}, too_large=frozenset())})
    outlines = Outlines(held, ROOT, parsing_in_tests())

    found = await asyncio.gather(search(outlines, "fail", TAKE), search(outlines, "failed", TAKE))

    assert (held.blobs_read_count, [len(each.names) for each in found]) == (1, [2, 2])


async def test_a_file_outlined_in_one_review_is_never_read_again_in_the_next() -> None:
    held = BlobsCounted({TAKE: FilesRead(contents={"src/attempts.py": ATTEMPTS}, too_large=frozenset())})
    parsing = parsing_in_tests()

    await search(Outlines(held, ROOT, parsing), "fail", TAKE)
    found_next = await search(Outlines(held, ROOT, parsing), "fail", TAKE)

    assert (held.blobs_read_count, len(found_next.names)) == (1, 2)


async def test_a_file_one_review_could_say_nothing_of_is_outlined_again_in_the_next(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A parse given up on a busy machine is no verdict on the file: what later reviews keep is only what was read."""
    held = TreesHeld({TAKE: FilesRead(contents={"src/attempts.py": ATTEMPTS}, too_large=frozenset())})
    parsing = parsing_in_tests()
    monkeypatch.setattr(reading, "LONGEST_PARSE_SECONDS", 0)
    await search(Outlines(held, ROOT, parsing), "fail", TAKE)
    monkeypatch.undo()

    found_next = await search(Outlines(held, ROOT, parsing), "fail", TAKE)

    assert len(found_next.names) == 2


async def test_a_search_answers_with_what_is_outlined_in_time_and_lists_the_rest_asked_again() -> None:
    held = BlobsSlow({TAKE: FilesRead(contents={"src/attempts.py": ATTEMPTS}, too_large=frozenset())})
    outlines = Outlines(held, ROOT, parsing_in_tests())

    found_at_once = await read_names_found(outlines, text="fail", tree=TAKE, touched=[], waits=AT_ONCE)
    found_again = await search(outlines, "fail", TAKE)

    assert (found_at_once, len(found_again.names), found_again.complete) == (
        FoundSoFar(names=[], more=0, complete=False),
        2,
        True,
    )


async def test_a_search_is_outlined_before_the_files_made_ready_ahead_of_it() -> None:
    files = {f"src/file_{number:03}.py": f"def fail_{number}():\n    pass\n".encode() for number in range(MANY_FILES)}
    held = TextSearched({TAKE: FilesRead(contents=files, too_large=frozenset())})
    chunks = ChunksRecorded(max_workers=WORKERS_IN_TESTS)
    outlines = Outlines(held, ROOT, NamesParsing(executor=chunks, workers=WORKERS_IN_TESTS, kept=OutlinesHeld()))

    await outlines.make_ready(TAKE)
    await search(outlines, "fail_199", TAKE)
    # Let what is made ready be outlined while the test's loop runs
    await outlines.of_files(TAKE, list(files))

    assert chunks.paths_given[0][0] == "src/file_199.py"


async def test_a_file_git_fails_to_read_fails_the_search_as_git_failed_while_another_file_is_read_apart() -> None:
    held = BlobsFailing(
        {TAKE: FilesRead(contents={"src/attempts.py": ATTEMPTS, "src/log.py": LOG}, too_large=frozenset())},
        failing=held_object_id(LOG),
    )
    outlines = Outlines(held, ROOT, parsing_in_tests())
    reading_attempts = asyncio.create_task(outlines.of_files(TAKE, ["src/attempts.py"]))
    await asyncio.sleep(0)

    with pytest.raises(GitError):
        await outlines.of_files(TAKE, ["src/attempts.py", "src/log.py"])
    await reading_attempts


async def test_an_answer_lists_twenty_names_those_starting_with_the_text_first_and_says_how_many_more_hold_it() -> None:
    holding_within = b"".join(f"def is_fail_{number}():\n    pass\n".encode() for number in range(NAMES_PAST_LISTED))
    starting = b"".join(f"def fail_{number}():\n    pass\n".encode() for number in range(NAMES_PAST_LISTED))
    held = held_tree(TAKE, {"src/a_within.py": holding_within, "src/b_starting.py": starting})

    found = await search(Outlines(held, ROOT, parsing_in_tests()), "fail", TAKE)

    assert (found.names, found.more) == (
        [
            defined(f"fail_{number}", DefinitionKind.FUNCTION, "src/b_starting.py", 2 * number + 1, 4)
            for number in range(20)
        ],
        22,
    )


async def test_a_search_of_a_tree_whose_every_file_is_outlined_asks_git_nothing() -> None:
    held = TextSearched(
        {TAKE: FilesRead(contents={"src/attempts.py": ATTEMPTS, "src/log.py": LOG}, too_large=frozenset())}
    )
    outlines = Outlines(held, ROOT, parsing_in_tests())
    await outlines.of_files(TAKE, ["src/attempts.py", "src/log.py"])

    found = await search(outlines, "fail", TAKE)

    assert (held.searches_count, len(found.names)) == (0, 5)


async def test_a_text_asked_again_while_its_files_are_outlined_is_searched_for_once() -> None:
    """As the page asks again until every file holding the text is outlined."""
    held = TextSearchedSlowly({TAKE: FilesRead(contents={"src/attempts.py": ATTEMPTS}, too_large=frozenset())})
    outlines = Outlines(held, ROOT, parsing_in_tests())

    await read_names_found(outlines, text="fail", tree=TAKE, touched=[], waits=AT_ONCE)
    found_again = await search(outlines, "fail", TAKE)

    assert (held.searches_count, len(found_again.names)) == (1, 2)

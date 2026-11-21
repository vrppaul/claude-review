"""The names a change touched in each file of it, judged against the file as the review's base holds it.

A reader reads a change by name as much as by file: under each file the
names outlining it that the change touched, and what became of each. What
became of one only the base can say: a name it outlined too is modified,
however much of it was rewritten, and one it did not is added. Each tree is
read in one asking of git, and every file by its grammar off the event
loop, as parsing is the CPU's work.
"""

import asyncio
import time
from pathlib import Path

import structlog

from claude_review.domain.code_names import FileNamesTouched, NameChange, TouchedName
from claude_review.domain.interfaces import TreesRead
from claude_review.domain.models import DiffFile, LinesTouched
from claude_review.services.code_names.languages import code_files_of
from claude_review.services.code_names.reading import OutlinedName, outline
from claude_review.services.code_names.timing import milliseconds_between

log = structlog.get_logger()


async def read_names_touched(
    repository: TreesRead, root: Path, *, tree: str, base: str, files: list[DiffFile]
) -> list[FileNamesTouched]:
    """The names the change touched in each of its files, in the order of its diff; a file with none left out.

    `tree` is what the take was written down as, `base` what the review reads it against.

    Raises:
        GitError: if git cannot read the files.
    """
    # A file showing no lines, not text or too large on either side, has none the change touched: it is never read
    read_as_code = [file for file in files if file.hunks and code_files_of(file.path) is not None]
    started = time.perf_counter()
    now, before = await asyncio.gather(
        repository.files_of(root, tree, [file.path for file in read_as_code]),
        repository.files_of(root, base, [file.path_before for file in read_as_code]),
    )
    read = time.perf_counter()
    named = await asyncio.to_thread(_names_in, read_as_code, now.contents, before.contents)
    log.debug(
        "names_touched_read",
        files=len(read_as_code),
        names=sum(len(file.names) for file in named),
        read_ms=milliseconds_between(started, read),
        parsed_ms=milliseconds_between(read, time.perf_counter()),
    )
    return named


def _names_in(files: list[DiffFile], now: dict[str, bytes], before: dict[str, bytes]) -> list[FileNamesTouched]:
    """The names the change touched in each of these files the take holds, a file with none left out."""
    named = (_names_of(file, now[file.path], before) for file in files if file.path in now)
    return [file for file in named if file is not None and file.names]


def _names_of(file: DiffFile, content: bytes, before: dict[str, bytes]) -> FileNamesTouched | None:
    """The names the change touched in one file; None where either side's parse was given up and nothing is known."""
    outlined_now = outline(file.path, content)
    outlined_before = _outline_before(file, before)
    if outlined_now is None or outlined_before is None:
        return None
    return FileNamesTouched(path=file.path, names=_names_touched(outlined_now, outlined_before, file.lines_touched()))


def _outline_before(file: DiffFile, before: dict[str, bytes]) -> list[OutlinedName] | None:
    """The names outlining the file as the base holds it: none where the base holds no such file, None where its
    parse was given up."""
    content = before.get(file.path_before)
    return [] if content is None else outline(file.path_before, content)


def _names_touched(now: list[OutlinedName], before: list[OutlinedName], lines: LinesTouched) -> list[TouchedName]:
    """The names outlining a file now that the change touched, in the order of the file."""
    outlined_before = {outlined.name: outlined for outlined in before}
    return [
        outlined.touched(change)
        for outlined in now
        if (change := _change_to(outlined, outlined_before.get(outlined.name), lines)) is not None
    ]


def _change_to(now: OutlinedName, before: OutlinedName | None, lines: LinesTouched) -> NameChange | None:
    """What the change did to a name outlining a file now, given how the base outlined it; None where nothing."""
    if before is None:
        return NameChange.ADDED
    if lines.touched(now.lines, before.lines):
        return NameChange.MODIFIED
    return None

"""The names a change touched in each file of it, judged against the file as the base it is read against holds it.

A reader reads a change by name as much as by file: under each file the
names outlining it that the change touched, and what became of each. What
became of one only the base can say: a name it outlined too is modified,
however much of it was rewritten, one it did not is added, and one it
outlined that the take does not is removed. Each tree is read in one asking
of git, and every file outlined once for the review's life (`Outlines`).
"""

import asyncio
import time
from typing import assert_never

import structlog

from claude_review.domain.code_names import FileNamesTouched, NameChange, TouchedName
from claude_review.domain.models import DiffFile, DiffHunk, LineSide, LinesTouched
from claude_review.services.code_names.languages import code_files_of
from claude_review.services.code_names.outlines import FilesOutlined, Outlines
from claude_review.services.code_names.reading import OutlinedName
from claude_review.services.code_names.timing import milliseconds_between

log = structlog.get_logger()

# Of a removed name and one standing now met at one line down a diff, the removed comes first, as git writes the
# lines a hunk removed before the lines that replace them
MET_FIRST = {LineSide.OLD: 0, LineSide.NEW: 1}


async def read_names_touched(
    outlines: Outlines, *, tree: str, base: str, files: list[DiffFile]
) -> list[FileNamesTouched]:
    """The names the change touched in each of its files, in the order of its diff; a file with none left out.

    `tree` is what the take was written down as, `base` what the diff `files` was read against.

    Raises:
        GitError: if git cannot read the files.
    """
    # A file showing no lines, not text or too large on either side, has none the change touched: it is never read
    read_as_code = [file for file in files if file.hunks and code_files_of(file.path) is not None]
    started = time.perf_counter()
    now, before = await asyncio.gather(
        outlines.of_files(tree, [file.path for file in read_as_code]),
        outlines.of_files(base, [file.path_before for file in read_as_code]),
    )
    said = (_names_of(file, now, before) for file in read_as_code)
    named = [touched for touched in said if touched is not None and touched.names]
    log.debug(
        "names_touched_read",
        files=len(read_as_code),
        names=sum(len(file.names) for file in named),
        outlined_ms=milliseconds_between(started, time.perf_counter()),
    )
    return named


def _names_of(file: DiffFile, now: FilesOutlined, before: FilesOutlined) -> FileNamesTouched | None:
    """The names the change touched in one file; None where either side is not known, so nothing can be said."""
    outlined_now = now.outline_of(file.path)
    outlined_before = before.outline_of(file.path_before)
    if outlined_now is None or outlined_before is None:
        return None
    return FileNamesTouched(path=file.path, names=_names_touched(outlined_now, outlined_before, file))


def _names_touched(now: list[OutlinedName], before: list[OutlinedName], file: DiffFile) -> list[TouchedName]:
    """The names outlining a file on either side that the change touched, in the order a reader meets them."""
    lines = file.lines_touched()
    outlined_before = {outlined.name: outlined for outlined in before}
    standing = {outlined.name for outlined in now}
    touched_now = [
        touched
        for outlined in now
        if (touched := _touched_now(outlined, outlined_before.get(outlined.name), lines)) is not None
    ]
    removed = [
        outlined.touched(NameChange.REMOVED, [outlined.lines_on(LineSide.OLD)])
        for outlined in before
        if outlined.name not in standing
    ]
    return sorted([*touched_now, *removed], key=lambda touched: _met_down_the_diff(touched, file.hunks))


def _touched_now(now: OutlinedName, before: OutlinedName | None, lines: LinesTouched) -> TouchedName | None:
    """A name outlining a file now as the change touched it, given how the base outlined it; None where untouched.

    A modified name stands on lines of either side, as a reader may be in it on a line the change removed.
    """
    if before is None:
        return now.touched(NameChange.ADDED, [now.lines_on(LineSide.NEW)])
    if lines.touched(now.spans, before.spans):
        return now.touched(NameChange.MODIFIED, [now.lines_on(LineSide.NEW), before.lines_on(LineSide.OLD)])
    return None


def _met_down_the_diff(touched: TouchedName, hunks: list[DiffHunk]) -> tuple[int, int]:
    """Where a reader going down a file's diff meets a name: the line of the new side it is written at or before."""
    match touched.side:
        case LineSide.NEW:
            line = touched.line
        case LineSide.OLD:
            line = _new_line_at(touched.line, hunks)
        case _:
            assert_never(touched.side)
    return line, MET_FIRST[touched.side]


def _new_line_at(old_line: int, hunks: list[DiffHunk]) -> int:
    """The line of the new side a reader going down the diff meets a line of the old side at: its own where both
    sides hold it, the one after the lines removed with it where the change removed it."""
    shift = 0
    for hunk in hunks:
        if old_line < hunk.old_start:
            break
        next_old, next_new = hunk.old_start, hunk.new_start
        for line in hunk.lines:
            if line.old_number == old_line:
                return next_new
            if line.old_number is not None:
                next_old = line.old_number + 1
            if line.new_number is not None:
                next_new = line.new_number + 1
        # Past a hunk, every line stands as far from its old number as the hunk's end does
        shift = next_new - next_old
    return old_line + shift

"""Git's unified diff read into the review's files: text in, files out, nothing else touched.

The repository runs git with its format pinned, so what is read here is the
shape git writes under those options: a part per file, opened by
"diff --git", its header lines, then its hunks.
"""

import re

from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, LineType

# Where each file's part of the diff begins
FILE_START = re.compile(r"^diff --git ", re.MULTILINE)
# "@@ -12,7 +12,8 @@ def handler():" — the line each side of a hunk starts at, and how many lines it has there
HUNK_HEADER = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)
# The count git leaves out of a hunk header: a side of one line
OMITTED_COUNT = 1
# The "a/x b/x" line with both paths quoted, which git does to a path that needs escapes
QUOTED_PATHS = re.compile(r'(?P<old>"(?:[^"\\]|\\.)*") (?P<new>"(?:[^"\\]|\\.)*")$')
# A path git quoted, and what is between the quotes
QUOTED_PATH = re.compile(r'"(?P<inside>.*)"', re.DOTALL)
# One piece of a quoted path: a byte in octal, an escaped character, or plain text
QUOTED_PIECE = re.compile(r"\\(?P<octal>[0-7]{3})|\\(?P<escaped>.)|(?P<plain>[^\\]+|\\$)", re.DOTALL)

# The markers naming the file after the change and before it, and the name of no file
NEW_SIDE_MARKER = "+++ "
OLD_SIDE_MARKER = "--- "
NO_FILE = "/dev/null"
# Headers that name where a file went when it moved or was copied without changing
MOVED_TO_HEADERS = ("rename to ", "copy to ")
# The header that names where a renamed file was
RENAMED_FROM_HEADER = "rename from "
# What git puts before the path on each side, and between the two in "a/x b/x"
OLD_SIDE_PREFIX = "a/"
NEW_SIDE_PREFIX = "b/"
SIDE_PREFIXES = (OLD_SIDE_PREFIX, NEW_SIDE_PREFIX)
NEW_SIDE_SEPARATOR = f" {NEW_SIDE_PREFIX}"
# The "a/x b/x" line read the shortest way, when nothing better is left
UNQUOTED_PATHS = re.compile(f"{re.escape(OLD_SIDE_PREFIX)}(?P<old>.+?){re.escape(NEW_SIDE_SEPARATOR)}(?P<new>.+)")
# A permission change: the file's mode before and after
OLD_MODE_HEADER = "old mode "
NEW_MODE_HEADER = "new mode "
# The mode of a file deleted, or created, whole. A file that changed type — a
# file become a link, a link become a file — git writes as two parts for one
# path, its deletion and then its creation, each with its mode.
DELETED_MODE_HEADER = "deleted file mode "
CREATED_MODE_HEADER = "new file mode "
BINARY_HEADER = "Binary files "
# A marker comes with a tab after the path when the path would otherwise be ambiguous
MARKER_PATH_END = "\t"

# What the header says happened to the file; a file it says none of was
# modified. A copy leaves the original in place, so what is new here is a file.
STATUS_HEADERS = {
    "new file": FileStatus.ADDED,
    "deleted file": FileStatus.DELETED,
    "rename from": FileStatus.RENAMED,
    "copy from": FileStatus.ADDED,
}

# What a line of a hunk is, by its first character. An empty line is a blank
# line of context that lost the space before it, as git writes one under
# diff.suppressBlankEmpty and `git apply` reads it. Anything else — "\ No
# newline at end of file" — is no line of the file.
LINE_KINDS = {"+": LineType.ADD, "-": LineType.DELETE, " ": LineType.CONTEXT, "": LineType.CONTEXT}

# What git writes as two characters inside a quoted path
ESCAPED_CHARACTERS = {
    "a": "\a",
    "b": "\b",
    "t": "\t",
    "n": "\n",
    "v": "\v",
    "f": "\f",
    "r": "\r",
    '"': '"',
    "\\": "\\",
}
OCTAL_BASE = 8
# Git writes a path's bytes as the file system holds them, here UTF-8; a
# byte that is not is shown replaced rather than lost with the whole diff
PATH_ENCODING = "utf-8"

# The line a file deleted or created whole starts at, on either side
FIRST_LINE = 1
# A hunk joined from two that git wrote has no header of git's own; it starts
# at the file's first line, where no header is drawn
JOINED_HUNK_HEADER = ""


class HunkStart(BaseModel):
    """A hunk's header: where it stands in its file's part of the diff, and the line each side starts at."""

    model_config = ConfigDict(frozen=True)

    # The header's line in the file's part of the diff
    index: int
    header: str
    # Each side's start as git writes it, and how many lines the hunk has there
    old_start: int
    old_count: int
    new_start: int
    new_count: int


class FilePart(BaseModel):
    """One file's part of the diff, read: the file it shows, and the mode it was deleted or created with."""

    model_config = ConfigDict(frozen=True)

    file: DiffFile
    deleted_mode: str | None
    created_mode: str | None


def parse_unified_diff(raw: str) -> list[DiffFile]:
    """Every file in git's unified diff, each once, in the order git wrote them."""
    written = (text for text in FILE_START.split(raw) if text.strip())
    return _each_path_once([part for text in written if (part := _part(text)) is not None])


def _part(text: str) -> FilePart | None:
    """One file's part of the diff, or None when no path can be read from it."""
    lines = text.split("\n")
    hunk_starts = [start for index, line in enumerate(lines) if (start := _hunk_start(index, line)) is not None]
    # Only what comes before the first hunk is the header. A removed line
    # reading "-- x" arrives as "--- x", and would otherwise pass for a path.
    header = lines[: hunk_starts[0].index] if hunk_starts else lines

    path = _path(header)
    if path is None:
        return None

    file = DiffFile(
        path=path,
        old_path=_old_path(header),
        status=_status(header),
        hunks=_hunks(lines, hunk_starts),
        is_binary=any(line.startswith(BINARY_HEADER) for line in header),
        # Only a change of mode: a file added or deleted whole has one mode,
        # which is no change
        old_mode=_mode(header, OLD_MODE_HEADER),
        new_mode=_mode(header, NEW_MODE_HEADER),
    )
    return FilePart(
        file=file, deleted_mode=_mode(header, DELETED_MODE_HEADER), created_mode=_mode(header, CREATED_MODE_HEADER)
    )


def _each_path_once(parts: list[FilePart]) -> list[DiffFile]:
    """The files the parts show, a path git wrote as deleted and then created read as one file whose type changed.

    The review knows a file by its path, so two files under one would be one
    key twice to whatever shows them.
    """
    files: list[DiffFile] = []
    previous: FilePart | None = None
    for part in parts:
        if previous is not None and _is_type_change(previous, part):
            files[-1] = _type_changed(previous, part)
        else:
            files.append(part.file)
        previous = part
    return files


def _is_type_change(deleted: FilePart, created: FilePart) -> bool:
    """Whether two parts git wrote one after the other are the deletion and the creation of one path."""
    return (
        deleted.deleted_mode is not None and created.created_mode is not None and deleted.file.path == created.file.path
    )


def _type_changed(deleted: FilePart, created: FilePart) -> DiffFile:
    """A file whose type changed: what it was, every line removed, and what it is, every line added, in one hunk.

    Each of git's two parts starts at the file's first line; as two hunks of
    one file they would both claim its top, so they are joined into one, as
    git writes a file rewritten whole. The modes say what changed.
    """
    lines = [line for part in (deleted, created) for hunk in part.file.hunks for line in hunk.lines]
    joined = DiffHunk(header=JOINED_HUNK_HEADER, old_start=FIRST_LINE, new_start=FIRST_LINE, lines=lines)
    return DiffFile(
        path=created.file.path,
        status=FileStatus.MODIFIED,
        hunks=[joined] if lines else [],
        is_binary=deleted.file.is_binary or created.file.is_binary,
        old_mode=deleted.deleted_mode,
        new_mode=created.created_mode,
    )


def _path(header: list[str]) -> str | None:
    """Where the file is now, read from its header.

    The "a/x b/x" line holds both paths with nothing but a space between
    them, so a name containing " b/" splits it wrongly. The markers carry
    exactly one path each and are preferred, in the order they answer
    "where is this file now":

    1. "+++" names the file after the change. A rename writes "--- a/old"
       and "+++ b/new", so the "+++" lines are all read before any "---"
       one, or the file is reported under a path git already moved.
    2. "---" covers a deletion, where "+++" is /dev/null.
    3. "rename to" and "copy to" cover a file moved or copied without a
       change, which has no markers at all.
    """
    for marker in (NEW_SIDE_MARKER, OLD_SIDE_MARKER):
        for line in header:
            if line.startswith(marker) and not line.startswith(marker + NO_FILE):
                return _without_side_prefix(_marker_path(line.removeprefix(marker)))

    for line in header:
        for moved_to in MOVED_TO_HEADERS:
            if line.startswith(moved_to):
                return _marker_path(line.removeprefix(moved_to))

    return _paths_line_path(header[0])


def _old_path(header: list[str]) -> str | None:
    """Where a renamed file was, read from its header; None for a file that did not move.

    A copy leaves its original where it was, so only a rename says where
    the file is no longer.
    """
    return next(
        (
            _marker_path(line.removeprefix(RENAMED_FROM_HEADER))
            for line in header
            if line.startswith(RENAMED_FROM_HEADER)
        ),
        None,
    )


def _marker_path(value: str) -> str:
    """The one path a marker names, without the tab git may end it with and unquoted."""
    return _unquote(value.split(MARKER_PATH_END, maxsplit=1)[0])


def _without_side_prefix(path: str) -> str:
    """The path without the "a/" or "b/" git puts before it."""
    for prefix in SIDE_PREFIXES:
        if path.startswith(prefix):
            return path.removeprefix(prefix)
    return path


def _paths_line_path(paths_line: str) -> str | None:
    """The path from the "a/x b/x" line.

    Only a file with no markers and no move reaches here — a binary file or
    a permission change — and for those the two halves name the same file.
    So the split is the one that makes them equal, which a name containing
    " b/" no longer defeats.
    """
    quoted = QUOTED_PATHS.match(paths_line)
    if quoted:
        return _without_side_prefix(_unquote(quoted["new"]))

    if paths_line.startswith(OLD_SIDE_PREFIX):
        pieces = paths_line.removeprefix(OLD_SIDE_PREFIX).split(NEW_SIDE_SEPARATOR)
        for split_at in range(1, len(pieces)):
            old_path = NEW_SIDE_SEPARATOR.join(pieces[:split_at])
            if old_path == NEW_SIDE_SEPARATOR.join(pieces[split_at:]):
                return old_path

    unquoted = UNQUOTED_PATHS.match(paths_line)
    return unquoted["new"] if unquoted else None


def _unquote(value: str) -> str:
    """Decode git's C-style path quoting: '"\\320\\266.py"' -> 'ж.py'.

    Git quotes a path when it holds characters it must escape, writing every
    byte outside plain ASCII as an octal escape. The bytes are collected
    first, because one character can span several escapes.
    """
    quoted = QUOTED_PATH.fullmatch(value)
    if quoted is None:
        return value

    decoded = bytearray()
    for piece in QUOTED_PIECE.finditer(quoted["inside"]):
        if piece["octal"]:
            decoded.append(int(piece["octal"], OCTAL_BASE))
        elif piece["escaped"]:
            decoded.extend(ESCAPED_CHARACTERS.get(piece["escaped"], piece["escaped"]).encode())
        else:
            decoded.extend(piece["plain"].encode())
    return decoded.decode(PATH_ENCODING, errors="replace")


def _status(header: list[str]) -> FileStatus:
    """What happened to the file, as its header says."""
    for line in header:
        for said, status in STATUS_HEADERS.items():
            if line.startswith(said):
                return status
    return FileStatus.MODIFIED


def _mode(header: list[str], mode_header: str) -> str | None:
    """The mode a header line of one kind gives the file, if the header has that line."""
    return next((line.removeprefix(mode_header).strip() for line in header if line.startswith(mode_header)), None)


def _hunk_start(index: int, line: str) -> HunkStart | None:
    """The hunk this line opens, if it is a hunk's header."""
    header = HUNK_HEADER.match(line)
    if header is None:
        return None
    return HunkStart(
        index=index,
        header=line,
        old_start=int(header["old_start"]),
        old_count=_count(header["old_count"]),
        new_start=int(header["new_start"]),
        new_count=_count(header["new_count"]),
    )


def _count(written: str | None) -> int:
    """How many lines a side of a hunk has, as its header says: one when it says nothing."""
    return OMITTED_COUNT if written is None else int(written)


def _hunks(lines: list[str], hunk_starts: list[HunkStart]) -> list[DiffHunk]:
    """Every hunk of a file, each read from the lines that follow its header, as far as its counts go."""
    # The lines a hunk may be read from run to the next header, the last
    # hunk's to the end of the file's part; its counts say where it ends
    boundaries = [*(start.index for start in hunk_starts), len(lines)]
    ends = boundaries[1:]
    return [_hunk(start, lines[start.index + 1 : end]) for start, end in zip(hunk_starts, ends, strict=True)]


def _hunk(start: HunkStart, body: list[str]) -> DiffHunk:
    """One hunk: as many lines of each side as its header counts, each numbered on the sides it is on.

    The counts say where the hunk ends, so what follows its last line — the
    empty piece after the line break that ends the file's part of the diff —
    is never read as a blank line of its own.
    """
    old_start, new_start = _first_line(start.old_start, start.old_count), _first_line(start.new_start, start.new_count)
    old_left, new_left = start.old_count, start.new_count
    old_number, new_number = old_start, new_start
    lines: list[DiffLine] = []

    for raw in body:
        if old_left == new_left == 0:
            break
        kind = LINE_KINDS.get(raw[:1])
        if kind is None:
            continue
        on_old_side = kind != LineType.ADD
        on_new_side = kind != LineType.DELETE
        lines.append(
            DiffLine(
                kind=kind,
                old_number=old_number if on_old_side else None,
                new_number=new_number if on_new_side else None,
                content=raw[1:],
            )
        )
        if on_old_side:
            old_number += 1
            old_left -= 1
        if on_new_side:
            new_number += 1
            new_left -= 1

    return DiffHunk(header=start.header, old_start=old_start, new_start=new_start, lines=lines)


def _first_line(start: int, count: int) -> int:
    """Where a side of a hunk starts: its first line, or where that would be when the side has none.

    Git starts a side with no lines at the line before it, which is nothing
    for an empty file; read as a first line, every count of lines above the
    hunk would come out one short.
    """
    return start + 1 if count == 0 else start

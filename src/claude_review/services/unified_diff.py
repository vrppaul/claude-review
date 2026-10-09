"""Git's unified diff read into the review's files: text in, files out, nothing else touched.

The repository runs git with its format pinned, so what is read here is the
shape git writes under those options: a part per file, opened by
"diff --git", its header lines, then its hunks.
"""

import itertools
import re

from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, LineType

# Where each file's part of the diff begins
FILE_START = re.compile(r"^diff --git ", re.MULTILINE)
# "@@ -12,7 +12,8 @@ def handler():" — the line each side of a hunk starts at
HUNK_HEADER = re.compile(r"^@@ -(?P<old_start>\d+)(?:,\d+)? \+(?P<new_start>\d+)(?:,\d+)? @@")
# The "a/x b/x" line with both paths quoted, which git does to a path that needs escapes
QUOTED_PATHS = re.compile(r'(?P<old>"(?:[^"\\]|\\.)*") (?P<new>"(?:[^"\\]|\\.)*")$')
# The "a/x b/x" line read the shortest way, when nothing better is left
UNQUOTED_PATHS = re.compile(r"a/(?P<old>.+?) b/(?P<new>.+)")
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
# What git puts before the path on each side, and between the two in "a/x b/x"
OLD_SIDE_PREFIX = "a/"
NEW_SIDE_PREFIX = "b/"
SIDE_PREFIXES = (OLD_SIDE_PREFIX, NEW_SIDE_PREFIX)
NEW_SIDE_SEPARATOR = f" {NEW_SIDE_PREFIX}"
# A permission change: the file's mode before and after
OLD_MODE_HEADER = "old mode "
NEW_MODE_HEADER = "new mode "
BINARY_HEADER = "Binary files "
# A marker comes with a tab after the path when the path would otherwise be ambiguous
MARKER_PATH_END = "\t"

# What the header says happened to the file; a file it says none of was
# modified. A copy leaves the original in place, so what is new here is a file.
STATUS_HEADERS = (
    ("new file", FileStatus.ADDED),
    ("deleted file", FileStatus.DELETED),
    ("rename from", FileStatus.RENAMED),
    ("copy from", FileStatus.ADDED),
)

# What a line of a hunk is, by its first character. Anything else —
# "\ No newline at end of file", the empty line the diff ends with — is not
# a line of the file.
LINE_KINDS = {"+": LineType.ADD, "-": LineType.DELETE, " ": LineType.CONTEXT}

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


def parse_unified_diff(raw: str) -> list[DiffFile]:
    """Every file in git's unified diff, in the order git wrote them."""
    parts = (part for part in FILE_START.split(raw) if part.strip())
    return [file for part in parts if (file := _file(part)) is not None]


def _file(part: str) -> DiffFile | None:
    """One file's part of the diff, or None when no path can be read from it."""
    lines = part.split("\n")
    hunk_headers = {index: header for index, line in enumerate(lines) if (header := HUNK_HEADER.match(line))}
    # Only what comes before the first hunk is the header. A removed line
    # reading "-- x" arrives as "--- x", and would otherwise pass for a path.
    header = lines[: min(hunk_headers, default=len(lines))]

    path = _path(header)
    if path is None:
        return None

    return DiffFile(
        path=path,
        status=_status(header),
        hunks=_hunks(lines, hunk_headers),
        is_binary=any(line.startswith(BINARY_HEADER) for line in header),
        old_mode=_mode(header, OLD_MODE_HEADER),
        new_mode=_mode(header, NEW_MODE_HEADER),
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


def _marker_path(value: str) -> str:
    """The one path a marker names, without the tab git may end it with and unquoted."""
    return _unquote(value.split(MARKER_PATH_END)[0])


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
    return decoded.decode("utf-8", errors="replace")


def _status(header: list[str]) -> FileStatus:
    """What happened to the file, as its header says."""
    for line in header:
        for said, status in STATUS_HEADERS:
            if line.startswith(said):
                return status
    return FileStatus.MODIFIED


def _mode(header: list[str], mode_header: str) -> str | None:
    """The mode one side of a permission change gives the file, if the header says one.

    A newly added file has "new file mode" instead, which is the file's only
    mode rather than a change, so it is not read here.
    """
    return next((line.removeprefix(mode_header).strip() for line in header if line.startswith(mode_header)), None)


def _hunks(lines: list[str], hunk_headers: dict[int, re.Match[str]]) -> list[DiffHunk]:
    """Every hunk of a file, each running from its header to the next one."""
    boundaries = [*hunk_headers, len(lines)]
    return [_hunk(hunk_headers[start], lines[start + 1 : end]) for start, end in itertools.pairwise(boundaries)]


def _hunk(header: re.Match[str], body: list[str]) -> DiffHunk:
    """One hunk, each of its lines numbered on the sides it is on."""
    old_start = int(header["old_start"])
    new_start = int(header["new_start"])
    old_number, new_number = old_start, new_start
    lines: list[DiffLine] = []

    for raw in body:
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
        if on_new_side:
            new_number += 1

    return DiffHunk(header=header.string, old_start=old_start, new_start=new_start, lines=lines)

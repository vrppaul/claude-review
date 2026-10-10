"""Git's unified diff, read back: whatever git writes for a set of changed files is read as those files.

The files are drawn — their paths, what happened to them, their hunks and
lines — and written out the way git writes them, so the parser is held to
git's format rather than to a handful of examples of it. How git writes was
taken from git itself: a path with a space in it ends its marker line with
a tab; a path holding a quote, a backslash, a control character or anything
past plain ASCII is quoted, the first two and the commonest controls
escaped in two characters and every other byte in octal; a hunk header
leaves out a count of one and may carry the line of the enclosing function
after it; a side with no lines is counted from nothing; and a file that
does not end in a newline says so after its last line.
"""

import string

from hypothesis import given, strategies as strategy
from pydantic import BaseModel

from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, LineType
from claude_review.services.unified_diff import parse_unified_diff

# What git puts before each side's path, and in place of a side that is not there
OLD_SIDE = "a/"
NEW_SIDE = "b/"
NO_FILE = "/dev/null"
# What git ends a marker's path with when the path holds a space
PATH_END = "\t"
# What each line of a hunk starts with, by kind
LINE_PREFIX = {LineType.CONTEXT: " ", LineType.ADD: "+", LineType.DELETE: "-"}
# What git writes after the last line of a file that does not end in a newline
NO_NEWLINE_MARKER = "\\ No newline at end of file"
# What the header of an added or deleted file says, as git writes it
NEW_FILE_HEADER = "new file mode 100644"
DELETED_FILE_HEADER = "deleted file mode 100644"
# An index line: git always writes one, and nothing reads it
INDEX_LINE = "index 1234567..89abcde 100644"
# What sets the line of the enclosing function apart from the hunk header before it
HEADING_SEPARATOR = " "

# The characters git writes in a path as they are, some it quotes for being
# past plain ASCII, and some it quotes for being a quote, a backslash or a control
PLAIN_PATH_CHARACTERS = string.ascii_letters + string.digits + "_.- "
FOREIGN_PATH_CHARACTERS = "жукёлщ"
ESCAPED_PATH_CHARACTERS = '"\\\t\a\r\x01\x7f'
# How git quotes a path: inside double quotes, each character it escapes after a backslash
QUOTE = '"'
ESCAPE = "\\"
# The characters git escapes in two characters, by the letter it writes after the backslash
TWO_CHARACTER_ESCAPES = {
    "\a": "a",
    "\b": "b",
    "\t": "t",
    "\n": "n",
    "\v": "v",
    "\f": "f",
    "\r": "r",
    '"': '"',
    "\\": "\\",
}
# Below this code a character is a control character, and so is the one that deletes
FIRST_PRINTABLE = 0x20
DELETE_CHARACTER = 0x7F

# How much of a diff is drawn at most: enough for every way the pieces meet
MOST_FILES = 3
MOST_HUNKS = 3
MOST_LINES = 6
MOST_SEGMENTS = 3
LONGEST_SEGMENT = 8
LONGEST_SKIP = 20

# One part of a path between slashes: never only dots or spaces, which git would not write as a name
segments = strategy.text(
    alphabet=PLAIN_PATH_CHARACTERS + FOREIGN_PATH_CHARACTERS + ESCAPED_PATH_CHARACTERS,
    min_size=1,
    max_size=LONGEST_SEGMENT,
).filter(lambda segment: segment.strip(". ") != "")
paths = strategy.lists(segments, min_size=1, max_size=MOST_SEGMENTS).map("/".join)
# What a line says: anything but the line break that ends it
contents = strategy.text(alphabet=strategy.characters(exclude_characters="\n"))
kinds = strategy.sampled_from(list(LineType))
# What follows a hunk header: nothing, or the line of the function the hunk is in
headings = strategy.one_of(strategy.just(""), contents.map(lambda heading: f"{HEADING_SEPARATOR}{heading}"))


class DrawnFile(BaseModel):
    """A file as drawn: what the parser must read, and whether the file ends without a newline."""

    file: DiffFile
    ends_without_newline: bool


def is_escaped(character: str) -> bool:
    """Whether git escapes the character when it writes a path."""
    code = ord(character)
    return (
        character in TWO_CHARACTER_ESCAPES
        or not character.isascii()
        or code < FIRST_PRINTABLE
        or code == DELETE_CHARACTER
    )


def escaped(character: str) -> str:
    """One character of a path as git writes it inside quotes."""
    if character in TWO_CHARACTER_ESCAPES:
        return ESCAPE + TWO_CHARACTER_ESCAPES[character]
    if is_escaped(character):
        return "".join(f"{ESCAPE}{byte:03o}" for byte in character.encode())
    return character


def as_git_quotes_it(path: str) -> str:
    """A path as git writes it: as it is, or quoted with every character it escapes written as git writes it."""
    if not any(is_escaped(character) for character in path):
        return path
    return QUOTE + "".join(escaped(character) for character in path) + QUOTE


def marker(side: str, path: str | None) -> str:
    """One side's path line: the side's prefix and the path, or no file."""
    if path is None:
        return NO_FILE
    return as_git_quotes_it(side + path) + (PATH_END if " " in path else "")


def counted(start: int, count: int) -> str:
    """One side of a hunk header: where it starts, and how many lines, unless that is one."""
    return f"{start}" if count == 1 else f"{start},{count}"


def hunk_header(old_start: int, new_start: int, lines: list[DiffLine], heading: str) -> str:
    old_count = sum(line.kind != LineType.ADD for line in lines)
    new_count = sum(line.kind != LineType.DELETE for line in lines)
    return f"@@ -{counted(old_start, old_count)} +{counted(new_start, new_count)} @@{heading}"


def numbered(kinds_and_contents: list[tuple[LineType, str]], old_start: int, new_start: int) -> list[DiffLine]:
    """The lines of a hunk, each numbered on the sides it is on."""
    lines: list[DiffLine] = []
    old_number, new_number = old_start, new_start
    for kind, content in kinds_and_contents:
        on_old_side, on_new_side = kind != LineType.ADD, kind != LineType.DELETE
        lines.append(
            DiffLine(
                kind=kind,
                old_number=old_number if on_old_side else None,
                new_number=new_number if on_new_side else None,
                content=content,
            )
        )
        old_number += on_old_side
        new_number += on_new_side
    return lines


@strategy.composite
def changed_hunks(draw: strategy.DrawFn) -> list[DiffHunk]:
    """A file's hunks, in order down the file, each a little way past the last."""
    hunks: list[DiffHunk] = []
    old_next = new_next = 1
    for _ in range(draw(strategy.integers(min_value=1, max_value=MOST_HUNKS))):
        skipped = draw(strategy.integers(min_value=0, max_value=LONGEST_SKIP))
        old_start, new_start = old_next + skipped, new_next + skipped
        drawn = draw(strategy.lists(strategy.tuples(kinds, contents), min_size=1, max_size=MOST_LINES))
        lines = numbered(drawn, old_start, new_start)
        hunks.append(
            DiffHunk(
                header=hunk_header(old_start, new_start, lines, draw(headings)),
                old_start=old_start,
                new_start=new_start,
                lines=lines,
            )
        )
        old_next = old_start + sum(line.kind != LineType.ADD for line in lines)
        new_next = new_start + sum(line.kind != LineType.DELETE for line in lines)
    return hunks


@strategy.composite
def modified_files(draw: strategy.DrawFn) -> DrawnFile:
    return DrawnFile(
        file=DiffFile(path=draw(paths), status=FileStatus.MODIFIED, hunks=draw(changed_hunks())),
        ends_without_newline=draw(strategy.booleans()),
    )


@strategy.composite
def one_sided_files(draw: strategy.DrawFn) -> DrawnFile:
    """A file whose one hunk has lines on one side only: added or deleted whole, or filled from empty or emptied."""
    status = draw(strategy.sampled_from([FileStatus.ADDED, FileStatus.DELETED, FileStatus.MODIFIED]))
    match status:
        case FileStatus.ADDED:
            kind = LineType.ADD
        case FileStatus.DELETED:
            kind = LineType.DELETE
        case _:
            kind = draw(strategy.sampled_from([LineType.ADD, LineType.DELETE]))
    said = draw(strategy.lists(contents, min_size=1, max_size=MOST_LINES))
    # Git counts the side that has no lines from nothing
    old_start, new_start = (0, 1) if kind == LineType.ADD else (1, 0)
    lines = numbered([(kind, content) for content in said], old_start, new_start)
    hunk = DiffHunk(
        header=hunk_header(old_start, new_start, lines, draw(headings)),
        old_start=old_start,
        new_start=new_start,
        lines=lines,
    )
    return DrawnFile(
        file=DiffFile(path=draw(paths), status=status, hunks=[hunk]), ends_without_newline=draw(strategy.booleans())
    )


def hunk_as_git_writes_it(hunk: DiffHunk) -> list[str]:
    return [hunk.header, *(LINE_PREFIX[line.kind] + line.content for line in hunk.lines)]


def file_as_git_writes_it(drawn: DrawnFile) -> list[str]:
    """One file's part of the diff: its header, then its hunks, and the mark of a last line with no newline."""
    changed = drawn.file
    old_path = None if changed.status == FileStatus.ADDED else changed.path
    new_path = None if changed.status == FileStatus.DELETED else changed.path
    status_headers = {FileStatus.ADDED: [NEW_FILE_HEADER], FileStatus.DELETED: [DELETED_FILE_HEADER]}
    header = [
        f"diff --git {as_git_quotes_it(OLD_SIDE + changed.path)} {as_git_quotes_it(NEW_SIDE + changed.path)}",
        *status_headers.get(changed.status, []),
        INDEX_LINE,
        f"--- {marker(OLD_SIDE, old_path)}",
        f"+++ {marker(NEW_SIDE, new_path)}",
    ]
    body = [text for hunk in changed.hunks for text in hunk_as_git_writes_it(hunk)]
    ending = [NO_NEWLINE_MARKER] if drawn.ends_without_newline else []
    return header + body + ending


def as_git_writes_it(drawn: list[DrawnFile]) -> str:
    return "\n".join(text for file in drawn for text in file_as_git_writes_it(file)) + "\n"


@given(drawn=strategy.lists(modified_files(), min_size=1, max_size=MOST_FILES, unique_by=lambda drawn: drawn.file.path))
def test_whatever_git_writes_for_changed_files_is_read_back_as_those_files(drawn: list[DrawnFile]) -> None:
    assert parse_unified_diff(as_git_writes_it(drawn)) == [file.file for file in drawn]


@given(drawn=one_sided_files())
def test_a_file_with_lines_on_one_side_only_is_read_under_its_path_with_what_happened_to_it(
    drawn: DrawnFile,
) -> None:
    assert parse_unified_diff(as_git_writes_it([drawn])) == [drawn.file]

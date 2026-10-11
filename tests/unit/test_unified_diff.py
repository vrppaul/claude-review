"""Git's unified diff, read back: whatever git writes for a set of changed files is read as those files.

The files are drawn — their paths, what happened to them, their hunks and
lines — and written out the way git writes them, so the parser is held to
git's format rather than to a handful of examples of it. How git writes was
taken from git itself: a path with a space in it ends its marker line with
a tab; a path holding a quote, a backslash, a control character or anything
past plain ASCII is quoted, the first two and the commonest controls
escaped in two characters and every other byte in octal; a hunk header
leaves out a count of one and may carry the line of the enclosing function
after it; a side with no lines starts at the line before where its lines
would be, which the review reads as where they would be; a blank line of
context may come bare, as under diff.suppressBlankEmpty; and a file that
does not end in a newline says so after its last line.
"""

import string

from hypothesis import given, strategies as strategy
from pydantic import BaseModel

from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, LineType
from claude_review.services.unified_diff import parse_unified_diff
from tests.helpers import added_line, context_line, removed_line

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

# Where a file's lines are numbered from
FIRST_LINE = 1
# How much of a diff is drawn at most: enough for every way the pieces meet
MOST_FILES = 3
MOST_HUNKS = 3
MOST_LINES = 6
MOST_SEGMENTS = 3
LONGEST_SEGMENT = 8
LONGEST_SKIP = 20
# A file whose hunk ends in a blank line, which git writes bare under
# diff.suppressBlankEmpty: a line changed two above the blank one that ends the file
ENDS_IN_A_BLANK = "notes.txt"
BLANK_ENDED_HUNK = [removed_line(1, "one"), added_line(1, "ONE"), context_line(2, 2, "two"), context_line(3, 3, "")]

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
    """A file as drawn: what the parser must read, and which of its sides end without a newline."""

    file: DiffFile
    old_side_ends_bare: bool
    new_side_ends_bare: bool


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
    """One side of a hunk header: where it starts, and how many lines, unless that is one.

    A side with no lines git starts at the line before where its lines would
    be: nothing, for a file that has none.
    """
    written_start = start - 1 if count == 0 else start
    return f"{written_start}" if count == 1 else f"{written_start},{count}"


def count_on_side(lines: list[DiffLine], *, without: LineType) -> int:
    """How many of the lines are on one side: every line but the other side's own."""
    return len([line for line in lines if line.kind != without])


def hunk_header(old_start: int, new_start: int, lines: list[DiffLine], heading: str) -> str:
    old_count = count_on_side(lines, without=LineType.ADD)
    new_count = count_on_side(lines, without=LineType.DELETE)
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
        if on_old_side:
            old_number += 1
        if on_new_side:
            new_number += 1
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
        old_next = old_start + count_on_side(lines, without=LineType.ADD)
        new_next = new_start + count_on_side(lines, without=LineType.DELETE)
    return hunks


@strategy.composite
def modified_files(draw: strategy.DrawFn) -> DrawnFile:
    return DrawnFile(
        file=DiffFile(path=draw(paths), status=FileStatus.MODIFIED, hunks=draw(changed_hunks())),
        old_side_ends_bare=draw(strategy.booleans()),
        new_side_ends_bare=draw(strategy.booleans()),
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
    # Both sides start at the first line: the one with lines, and the one whose lines would
    lines = numbered([(kind, content) for content in said], FIRST_LINE, FIRST_LINE)
    hunk = DiffHunk(
        header=hunk_header(FIRST_LINE, FIRST_LINE, lines, draw(headings)),
        old_start=FIRST_LINE,
        new_start=FIRST_LINE,
        lines=lines,
    )
    return DrawnFile(
        file=DiffFile(path=draw(paths), status=status, hunks=[hunk]),
        old_side_ends_bare=draw(strategy.booleans()),
        new_side_ends_bare=draw(strategy.booleans()),
    )


def line_as_git_writes_it(line: DiffLine, *, bare_blanks: bool) -> str:
    """One line of a hunk: its kind's mark and what it says, or nothing for a blank line of context written bare."""
    if bare_blanks and line.kind == LineType.CONTEXT and not line.content:
        return ""
    return LINE_PREFIX[line.kind] + line.content


def hunk_as_git_writes_it(hunk: DiffHunk, *, bare_blanks: bool, marked: set[int]) -> list[str]:
    """A hunk's header and lines, git's mark of a side ending without a newline after each marked line."""
    written = [hunk.header]
    for index, line in enumerate(hunk.lines):
        written.append(line_as_git_writes_it(line, bare_blanks=bare_blanks))
        if index in marked:
            written.append(NO_NEWLINE_MARKER)
    return written


def last_on_side(hunk: DiffHunk, *, without: LineType) -> int | None:
    """Where in the hunk the last line of one side is: the last line of any kind but the other side's own."""
    return max((index for index, line in enumerate(hunk.lines) if line.kind != without), default=None)


def marked_ends(drawn: DrawnFile, hunk: DiffHunk) -> set[int]:
    """The lines of a file's last hunk git marks: the last line of each side that ends without a newline."""
    ends = [
        last_on_side(hunk, without=LineType.ADD) if drawn.old_side_ends_bare else None,
        last_on_side(hunk, without=LineType.DELETE) if drawn.new_side_ends_bare else None,
    ]
    return {index for index in ends if index is not None}


def file_as_git_writes_it(drawn: DrawnFile, *, bare_blanks: bool) -> list[str]:
    """One file's part of the diff: its header, then its hunks, the last line of a side with no newline marked."""
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
    last = changed.hunks[-1]
    body = [
        text
        for hunk in changed.hunks
        for text in hunk_as_git_writes_it(
            hunk, bare_blanks=bare_blanks, marked=marked_ends(drawn, hunk) if hunk is last else set()
        )
    ]
    return header + body


def as_git_writes_it(drawn: list[DrawnFile], *, bare_blanks: bool) -> str:
    """The whole diff; with bare blanks, as git writes it under diff.suppressBlankEmpty."""
    return "\n".join(text for file in drawn for text in file_as_git_writes_it(file, bare_blanks=bare_blanks)) + "\n"


@given(
    drawn=strategy.lists(modified_files(), min_size=1, max_size=MOST_FILES, unique_by=lambda drawn: drawn.file.path),
    bare_blanks=strategy.booleans(),
)
def test_whatever_git_writes_for_changed_files_is_read_back_as_those_files(
    drawn: list[DrawnFile], *, bare_blanks: bool
) -> None:
    assert parse_unified_diff(as_git_writes_it(drawn, bare_blanks=bare_blanks)) == [file.file for file in drawn]


def test_a_blank_line_that_ends_a_hunk_is_one_of_its_lines_and_the_end_of_the_diff_is_not() -> None:
    """Written bare, the blank is an empty line, and so is what follows the line break that ends the diff."""
    hunk = DiffHunk(
        header=hunk_header(FIRST_LINE, FIRST_LINE, BLANK_ENDED_HUNK, heading=""),
        old_start=FIRST_LINE,
        new_start=FIRST_LINE,
        lines=BLANK_ENDED_HUNK,
    )
    drawn = DrawnFile(
        file=DiffFile(path=ENDS_IN_A_BLANK, status=FileStatus.MODIFIED, hunks=[hunk]),
        old_side_ends_bare=False,
        new_side_ends_bare=False,
    )

    assert parse_unified_diff(as_git_writes_it([drawn], bare_blanks=True)) == [drawn.file]


@given(drawn=one_sided_files(), bare_blanks=strategy.booleans())
def test_a_file_with_lines_on_one_side_only_is_read_under_its_path_with_what_happened_to_it(
    drawn: DrawnFile, *, bare_blanks: bool
) -> None:
    assert parse_unified_diff(as_git_writes_it([drawn], bare_blanks=bare_blanks)) == [drawn.file]


# What git 2.43 writes for a file of three lines turned into a link to
# target.txt, and for such a link turned into a file of two lines, beside a
# file changed the ordinary way: each change of type as a deletion and then a
# creation of the same path
FILE_TURNED_INTO_A_LINK = """\
diff --git a/becomes-link.txt b/becomes-link.txt
deleted file mode 100644
index 4cb29ea..0000000
--- a/becomes-link.txt
+++ /dev/null
@@ -1,3 +0,0 @@
-one
-two
-three
diff --git a/becomes-link.txt b/becomes-link.txt
new file mode 120000
index 0000000..4cbb553
--- /dev/null
+++ b/becomes-link.txt
@@ -0,0 +1 @@
+target.txt
\\ No newline at end of file
diff --git a/zz.txt b/zz.txt
index 7898192..422c2b7 100644
--- a/zz.txt
+++ b/zz.txt
@@ -1 +1,2 @@
 a
+b
"""
LINK_TURNED_INTO_A_FILE = """\
diff --git a/was-link b/was-link
deleted file mode 120000
index 4cbb553..0000000
--- a/was-link
+++ /dev/null
@@ -1 +0,0 @@
-target.txt
\\ No newline at end of file
diff --git a/was-link b/was-link
new file mode 100644
index 0000000..957dd0a
--- /dev/null
+++ b/was-link
@@ -0,0 +1,2 @@
+now a file
+second
"""
# Git's modes for a file and for a link
FILE_MODE = "100644"
LINK_MODE = "120000"


def test_a_file_turned_into_a_link_is_one_file_whose_lines_become_the_link() -> None:
    """Two files under one path would be one key twice on the page, which then draws nothing at all."""
    [turned, ordinary] = parse_unified_diff(FILE_TURNED_INTO_A_LINK)

    assert (turned.path, turned.status) == ("becomes-link.txt", FileStatus.MODIFIED)
    assert (turned.old_mode, turned.new_mode) == (FILE_MODE, LINK_MODE)
    assert [line for hunk in turned.hunks for line in hunk.lines] == [
        removed_line(1, "one"),
        removed_line(2, "two"),
        removed_line(3, "three"),
        added_line(1, "target.txt"),
    ]
    assert len(turned.hunks) == 1, "two hunks would both claim the top of the file"
    assert ordinary.path == "zz.txt"


def test_a_link_turned_into_a_file_is_one_file_whose_link_becomes_its_lines() -> None:
    [turned] = parse_unified_diff(LINK_TURNED_INTO_A_FILE)

    assert (turned.path, turned.status) == ("was-link", FileStatus.MODIFIED)
    assert (turned.old_mode, turned.new_mode) == (LINK_MODE, FILE_MODE)
    assert [line for hunk in turned.hunks for line in hunk.lines] == [
        removed_line(1, "target.txt"),
        added_line(1, "now a file"),
        added_line(2, "second"),
    ]
    assert len(turned.hunks) == 1


# What git writes for a file moved under a name it has to quote, with a line
# of it changed, and for one moved without a change
RENAMED_AND_CHANGED = """\
diff --git a/old_name.txt "b/\\320\\266 new.txt"
similarity index 75%
rename from old_name.txt
rename to "\\320\\266 new.txt"
index 2f0c7ea..b2a5f3c 100644
--- a/old_name.txt
+++ "b/\\320\\266 new.txt"
@@ -1,2 +1,2 @@
 kept
-was
+is
"""
RENAMED_UNCHANGED = """\
diff --git a/before.txt b/after.txt
similarity index 100%
rename from before.txt
rename to after.txt
"""


def test_a_renamed_file_says_where_it_was() -> None:
    [changed] = parse_unified_diff(RENAMED_AND_CHANGED)
    [moved] = parse_unified_diff(RENAMED_UNCHANGED)

    assert (changed.path, changed.old_path) == ("ж new.txt", "old_name.txt")
    assert (moved.path, moved.old_path) == ("after.txt", "before.txt")


COPIED_UNCHANGED = """\
diff --git a/original.txt b/copy.txt
similarity index 100%
copy from original.txt
copy to copy.txt
"""


def test_a_file_that_did_not_move_has_no_old_path() -> None:
    """A copy leaves its original where it was: it is a new file, not one that moved."""
    [turned, ordinary] = parse_unified_diff(FILE_TURNED_INTO_A_LINK)
    [copied] = parse_unified_diff(COPIED_UNCHANGED)

    assert (turned.old_path, ordinary.old_path, copied.old_path) == (None, None, None)

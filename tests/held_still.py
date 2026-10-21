"""A repository held still: a change under review that git is never asked about, as a test puts it together.

A review of a change reads it from its repository, and takes it again from
there whenever it is opened, compared or retaken; there is no review of a
change without one. A test that is about anything but git hands the change
it means as files, and this repository gives them back: staged, its tree
yields them as git writes a diff, so the review reads them through the
parser it reads every diff through, and nothing in its working tree ever
moves. What the files cannot say of themselves — which of the ones git
calls binary are too large to read — the test says.
"""

import contextlib
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import override

from claude_review.domain.interfaces import ReviewedRepository, StagedTree
from claude_review.domain.models import (
    Checkout,
    DiffFile,
    DiffHunk,
    FileStatus,
    GitRef,
    LineType,
    OnBranch,
    Unshown,
)
from claude_review.services.review_opening import OpenedRepository, ReviewOpening

# Where the repository held still stands, the commit its change is taken against, and the tree it stages
HELD_STILL_ROOT = Path("/repository-held-still")
HELD_STILL_BASE = "base-held-still"
HELD_STILL_TREE = "tree-held-still"
EMPTY_TREE = "empty-tree-held-still"
# The branch it has checked out
HELD_STILL_BRANCH = "main"
# What makes a review of it the same review as another: nothing, since none is opened twice
HELD_STILL_IDENTITY = "a change held still"

# How git writes a diff: each file's part under its header, each path quoted, every line of a hunk after the
# mark of its kind, and a hunk's header with how many lines it has on each side
FILE_HEADER = "diff --git {old} {new}"
OLD_SIDE = "a/"
NEW_SIDE = "b/"
NO_FILE = "/dev/null"
OLD_MARKER = "--- {old}"
NEW_MARKER = "+++ {new}"
HUNK_HEADER = "@@ -{old_start},{old_count} +{new_start},{new_count} @@"
BINARY_LINE = "Binary files {old} and {new} differ"
LINE_MARKS = {LineType.CONTEXT: " ", LineType.ADD: "+", LineType.DELETE: "-"}
# Which sides of a hunk a line of each kind is on, counted
ON_THE_OLD_SIDE = {LineType.CONTEXT: 1, LineType.DELETE: 1, LineType.ADD: 0}
ON_THE_NEW_SIDE = {LineType.CONTEXT: 1, LineType.ADD: 1, LineType.DELETE: 0}
# A path in a header, quoted as git quotes one it must: every one, here, which git's reader takes the same way
QUOTED = '"{side}{path}"'
ESCAPES = str.maketrans({"\\": "\\\\", '"': '\\"', "\t": "\\t", "\n": "\\n"})
LINE_BREAK = "\n"
# The mode a file is created or deleted with
FILE_MODE = "100644"
# What git says before the markers of a file of each status, and which of its sides there is a file on
STATUS_HEADERS: dict[FileStatus, tuple[str, ...]] = {
    FileStatus.MODIFIED: (),
    FileStatus.ADDED: (f"new file mode {FILE_MODE}",),
    FileStatus.DELETED: (f"deleted file mode {FILE_MODE}",),
    FileStatus.RENAMED: ("similarity index 90%", "rename from {old_bare}", "rename to {new_bare}"),
}
OLD_SIDE_OF = {
    FileStatus.MODIFIED: "{old}",
    FileStatus.ADDED: NO_FILE,
    FileStatus.DELETED: "{old}",
    FileStatus.RENAMED: "{old}",
}
NEW_SIDE_OF = {
    FileStatus.MODIFIED: "{new}",
    FileStatus.ADDED: "{new}",
    FileStatus.DELETED: NO_FILE,
    FileStatus.RENAMED: "{new}",
}
# Where a file of each status was before the change: where it is, but where a renamed one came from
WAS_AT = {
    FileStatus.MODIFIED: lambda file: file.path,
    FileStatus.ADDED: lambda file: file.path,
    FileStatus.DELETED: lambda file: file.path,
    FileStatus.RENAMED: lambda file: file.old_path,
}


def change_held_still(diff_files: list[DiffFile], *, title: str) -> ReviewOpening:
    """What a review of these files as a repository's change opens on: the repository held still."""
    return ReviewOpening(
        source=OpenedRepository(
            root=HELD_STILL_ROOT,
            named_base=None,
            pinned_base=HELD_STILL_BASE,
            checkout=OnBranch(branch=HELD_STILL_BRANCH),
        ),
        diff_files=diff_files,
        title=title,
        identity=HELD_STILL_IDENTITY,
    )


def unified_diff_of(diff_files: list[DiffFile]) -> str:
    """The files as git writes them in a diff."""
    return "".join(_file_part(file) for file in diff_files)


def _file_part(file: DiffFile) -> str:
    """One file's part of a diff: its header, what git says of its status, then its markers and hunks or why not."""
    old_bare, new_bare = WAS_AT[file.status](file), file.path
    old = _quoted(OLD_SIDE, old_bare)
    new = _quoted(NEW_SIDE, new_bare)
    old_side = OLD_SIDE_OF[file.status].format(old=old)
    new_side = NEW_SIDE_OF[file.status].format(new=new)
    said = [
        FILE_HEADER.format(old=old, new=new),
        *(line.format(old_bare=old_bare, new_bare=new_bare) for line in STATUS_HEADERS[file.status]),
        *_body(file, old_side, new_side),
    ]
    return "".join(f"{line}{LINE_BREAK}" for line in said)


def _body(file: DiffFile, old_side: str, new_side: str) -> list[str]:
    """What follows a file's header: why its lines are not shown, or its markers and its hunks."""
    shown = [OLD_MARKER.format(old=old_side), NEW_MARKER.format(new=new_side), *_hunk_lines(file.hunks)]
    unread = [BINARY_LINE.format(old=old_side, new=new_side)]
    return {None: shown, Unshown.BINARY: unread, Unshown.TOO_LARGE: unread}[file.unshown]


def _hunk_lines(hunks: list[DiffHunk]) -> list[str]:
    """Every hunk, its header counting the lines on each side, then each line after the mark of its kind."""
    return [line for hunk in hunks for line in (_hunk_header(hunk), *_marked(hunk))]


def _hunk_header(hunk: DiffHunk) -> str:
    return HUNK_HEADER.format(
        old_start=hunk.old_start,
        old_count=sum(ON_THE_OLD_SIDE[line.kind] for line in hunk.lines),
        new_start=hunk.new_start,
        new_count=sum(ON_THE_NEW_SIDE[line.kind] for line in hunk.lines),
    )


def _marked(hunk: DiffHunk) -> list[str]:
    return [f"{LINE_MARKS[line.kind]}{line.content}" for line in hunk.lines]


def _quoted(side: str, path: str) -> str:
    return QUOTED.format(side=side, path=path.translate(ESCAPES))


class StagingHeldStill(StagedTree):
    """The tree of a repository held still, staged: the same files against whatever base, nothing moved since."""

    def __init__(self, diff_files: list[DiffFile], too_large: frozenset[str]) -> None:
        self._diff = unified_diff_of(diff_files)
        self._too_large = too_large

    @override
    async def diff(self, base: str, *, ignore_whitespace: bool) -> str:
        return self._diff

    @override
    async def write_tree(self) -> str:
        return HELD_STILL_TREE

    @override
    async def names_changed_since(self, bases: list[str]) -> dict[str, list[str]]:
        return {base: [] for base in bases}

    @override
    async def too_large_to_show(self, base: str, files: list[DiffFile]) -> set[str]:
        return {file.path for file in files} & self._too_large


class RepositoryHeldStill(ReviewedRepository):
    """A repository whose working tree never moves, and whose change is the files it was made with."""

    def __init__(self, diff_files: list[DiffFile], *, too_large: frozenset[str]) -> None:
        self._diff_files = diff_files
        self._too_large = too_large

    @override
    @contextlib.asynccontextmanager
    async def staged(self, path: Path) -> AsyncGenerator[StagingHeldStill]:
        yield StagingHeldStill(self._diff_files, self._too_large)

    @override
    async def top_level(self, path: Path) -> Path | None:
        return path

    @override
    async def changed_paths(self, path: Path) -> list[str]:
        return []

    @override
    async def list_refs(self, path: Path) -> list[GitRef]:
        return []

    @override
    async def commit_named(self, path: Path, revision: str) -> str | None:
        return HELD_STILL_BASE

    @override
    async def empty_tree(self, path: Path) -> str:
        return EMPTY_TREE

    @override
    async def checked_out(self, path: Path) -> Checkout:
        return OnBranch(branch=HELD_STILL_BRANCH)

    @override
    async def diff_between(self, path: Path, earlier: str, later: str) -> str:
        return ""

    @override
    async def is_tracked(self, root: Path, relative_path: str) -> bool:
        return True

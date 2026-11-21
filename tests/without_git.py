"""Repositories a test puts in git's place: every test that is about anything but git.

A review of a change reads it from its repository, and takes it again from
there whenever it is opened, compared or retaken; there is no review of a
change without one. A test about anything else hands the review a
repository git is never asked about: at one root, on one branch, its one
commit whatever base is named, nothing changed outside what it stages. What
it stages is the one thing each kind of it says.

A test of a change hands its files to a repository held still: staged, its
tree yields them as git writes a diff, so the review reads them through the
parser it reads every diff through, and nothing in its working tree ever
moves. What git alone decides — a file's mode, a rename, what a base names —
is tested on git itself, so nothing here writes it.
"""

import contextlib
import hashlib
from collections import defaultdict
from collections.abc import AsyncGenerator, Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import override

from claude_review.domain.interfaces import OutlinesKept, ReviewedRepository, StagedTree, TreesRead
from claude_review.domain.models import (
    BlobsAt,
    Checkout,
    DiffFile,
    DiffHunk,
    FilesRead,
    FileStatus,
    GitRef,
    LineType,
    OnBranch,
    Unshown,
)
from claude_review.services.code_names.outlines import NamesParsing
from claude_review.services.review_opening import OpenedRepository, ReviewOpening

# Where a repository without git stands, the one commit any base it is asked for names, the tree of nothing, and
# what it has checked out
ROOT = Path("/repository-without-git")
ITS_COMMIT = "its-commit"
EMPTY_TREE = "empty-tree"
ITS_CHECKOUT = OnBranch(branch="main")
# The tree a repository held still stages: always the same, since nothing in it moves
TREE_HELD_STILL = "tree-held-still"
# What makes a review of a change held still the same review as another: nothing, since none is opened twice
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
# What git says of a file of each status the tests hand over before its markers, and which of its sides there is
# a file on: a file changed, or one added with the mode of a plain file
STATUS_HEADERS: dict[FileStatus, tuple[str, ...]] = {
    FileStatus.MODIFIED: (),
    FileStatus.ADDED: ("new file mode 100644",),
}
OLD_SIDE_OF = {FileStatus.MODIFIED: "{old}", FileStatus.ADDED: NO_FILE}
NEW_SIDE_OF = {FileStatus.MODIFIED: "{new}", FileStatus.ADDED: "{new}"}


def opened_without_git() -> OpenedRepository:
    """A repository without git as a review opens on it: its uncommitted changes, against its one commit."""
    return OpenedRepository(root=ROOT, named_base=None, pinned_base=ITS_COMMIT, checkout=ITS_CHECKOUT)


def change_held_still(diff_files: list[DiffFile], *, title: str) -> ReviewOpening:
    """What a review of these files as a repository's change opens on: the repository held still."""
    return ReviewOpening(source=opened_without_git(), diff_files=diff_files, title=title, identity=HELD_STILL_IDENTITY)


def unified_diff_of(diff_files: list[DiffFile]) -> str:
    """The files as git writes them in a diff."""
    return "".join(_file_part(file) for file in diff_files)


def _file_part(file: DiffFile) -> str:
    """One file's part of a diff: its header, what git says of its status, then its markers and hunks or why not."""
    old = _quoted(OLD_SIDE, file.path)
    new = _quoted(NEW_SIDE, file.path)
    old_side = OLD_SIDE_OF[file.status].format(old=old)
    new_side = NEW_SIDE_OF[file.status].format(new=new)
    said = [
        FILE_HEADER.format(old=old, new=new),
        *STATUS_HEADERS[file.status],
        *BODY_OF[file.unshown](file, old_side, new_side),
    ]
    return "".join(f"{line}{LINE_BREAK}" for line in said)


def _shown(file: DiffFile, old_side: str, new_side: str) -> list[str]:
    """What follows the header of a file whose lines are shown: its markers, then every hunk."""
    return [OLD_MARKER.format(old=old_side), NEW_MARKER.format(new=new_side), *_hunk_lines(file.hunks)]


def _unread(file: DiffFile, old_side: str, new_side: str) -> list[str]:
    """What follows the header of a file git does not read: that it is binary, which a file too large is to git."""
    return [BINARY_LINE.format(old=old_side, new=new_side)]


# What follows a file's header, by why its lines are not shown, if they are not
BODY_OF: dict[Unshown | None, Callable[[DiffFile, str, str], list[str]]] = {
    None: _shown,
    Unshown.BINARY: _unread,
    Unshown.TOO_LARGE: _unread,
}


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


def _too_large_in(diff_files: list[DiffFile]) -> frozenset[str]:
    """The files git shows as binary that are too large to read, as the files say of themselves."""
    paths_by_why_unshown: defaultdict[Unshown | None, set[str]] = defaultdict(set)
    for file in diff_files:
        paths_by_why_unshown[file.unshown].add(file.path)
    return frozenset(paths_by_why_unshown[Unshown.TOO_LARGE])


class RepositoryWithoutGit(ReviewedRepository):
    """A repository git is never asked about: what it stages is each kind's own, and all else is the same."""

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
        return ITS_COMMIT

    @override
    async def empty_tree(self, path: Path) -> str:
        return EMPTY_TREE

    @override
    async def checked_out(self, path: Path) -> Checkout:
        return ITS_CHECKOUT

    @override
    async def diff_between(self, path: Path, earlier: str, later: str, *, ignore_whitespace: bool) -> str:
        return ""

    @override
    async def names_changed_between(self, path: Path, earlier: list[str], later: str) -> dict[str, list[str]]:
        return {base: [] for base in earlier}

    @override
    async def too_large_between(self, path: Path, earlier: str, later: str, files: list[DiffFile]) -> set[str]:
        return set()

    @override
    async def paths_holding(self, root: Path, tree: str, word: str) -> list[str]:
        return []

    @override
    async def paths_with_text(self, root: Path, tree: str, text: str) -> list[str]:
        return []

    @override
    async def files_of(self, root: Path, tree: str, paths: list[str]) -> FilesRead:
        return FilesRead(contents={}, too_large=frozenset())

    @override
    async def blobs_at(self, root: Path, tree: str, paths: list[str]) -> BlobsAt:
        return BlobsAt(object_ids={}, too_large=frozenset())

    @override
    async def blobs_read(self, root: Path, object_ids: list[str]) -> list[bytes]:
        return []

    @override
    async def files_in(self, root: Path, tree: str) -> frozenset[str]:
        return frozenset()


class OutlinesHeld(OutlinesKept):
    """Outlines kept in memory, for one test alone."""

    def __init__(self) -> None:
        self._kept: dict[str, bytes] = {}

    @override
    async def read(self, keys: list[str]) -> dict[str, bytes]:
        return {key: self._kept[key] for key in keys if key in self._kept}

    @override
    async def keep(self, kept: dict[str, bytes]) -> None:
        self._kept.update(kept)


# The threads a test's review parses names in: one interpreter's, so a test spawns no processes
WORKERS_IN_TESTS = 2
PARSED_IN_TESTS = ThreadPoolExecutor(max_workers=WORKERS_IN_TESTS)


def parsing_in_tests() -> NamesParsing:
    """How a test's review parses names: in threads, keeping what it outlined for itself alone."""
    return NamesParsing(executor=PARSED_IN_TESTS, workers=WORKERS_IN_TESTS, kept=OutlinesHeld())


def held_object_id(content: bytes) -> str:
    """The id an object store keeps a content by: the same for the same bytes, whichever tree and path hold them."""
    return hashlib.sha1(content, usedforsecurity=False).hexdigest()


class TreesHeld(TreesRead):
    """Trees held in memory, by their ids, each as what reading every path of it gives; every file holds any word or
    text."""

    def __init__(self, trees: dict[str, FilesRead]) -> None:
        self._trees = trees
        self._objects = {
            held_object_id(content): content for held in trees.values() for content in held.contents.values()
        }

    @override
    async def paths_holding(self, root: Path, tree: str, word: str) -> list[str]:
        return list(self._trees[tree].contents)

    @override
    async def paths_with_text(self, root: Path, tree: str, text: str) -> list[str]:
        return list(self._trees[tree].contents)

    @override
    async def files_of(self, root: Path, tree: str, paths: list[str]) -> FilesRead:
        held = self._trees[tree]
        return FilesRead(
            # In the order asked, as git answers
            contents={path: held.contents[path] for path in paths if path in held.contents},
            too_large=held.too_large & set(paths),
        )

    @override
    async def blobs_at(self, root: Path, tree: str, paths: list[str]) -> BlobsAt:
        read = await self.files_of(root, tree, paths)
        return BlobsAt(
            object_ids={path: held_object_id(content) for path, content in read.contents.items()},
            too_large=read.too_large,
        )

    @override
    async def blobs_read(self, root: Path, object_ids: list[str]) -> list[bytes]:
        return [self._objects[object_id] for object_id in object_ids]

    @override
    async def files_in(self, root: Path, tree: str) -> frozenset[str]:
        held = self._trees[tree]
        return frozenset(held.contents) | held.too_large


class StagingHeldStill(StagedTree):
    """The tree of a repository held still, staged: the same files against whatever base, nothing moved since."""

    def __init__(self, diff_files: list[DiffFile]) -> None:
        self._diff = unified_diff_of(diff_files)
        self._too_large = _too_large_in(diff_files)

    @override
    async def diff(self, base: str, *, ignore_whitespace: bool) -> str:
        return self._diff

    @override
    async def write_tree(self) -> str:
        return TREE_HELD_STILL

    @override
    async def names_changed_since(self, bases: list[str]) -> dict[str, list[str]]:
        return {base: [] for base in bases}

    @override
    async def too_large_to_show(self, base: str, files: list[DiffFile]) -> set[str]:
        return {file.path for file in files} & self._too_large


class RepositoryHeldStill(RepositoryWithoutGit):
    """A repository whose working tree never moves, and whose change is the files it was made with."""

    def __init__(self, diff_files: list[DiffFile]) -> None:
        self._diff_files = diff_files
        # What the tree it stages holds against each thing it can be read against: its change against its one
        # commit, and nothing against the tree itself, which never moves
        self._diff_against = {ITS_COMMIT: unified_diff_of(diff_files), TREE_HELD_STILL: ""}
        self._too_large = _too_large_in(diff_files)

    @override
    @contextlib.asynccontextmanager
    async def staged(self, path: Path) -> AsyncGenerator[StagingHeldStill]:
        yield StagingHeldStill(self._diff_files)

    @override
    async def diff_between(self, path: Path, earlier: str, later: str, *, ignore_whitespace: bool) -> str:
        return self._diff_against[earlier]

    @override
    async def too_large_between(self, path: Path, earlier: str, later: str, files: list[DiffFile]) -> set[str]:
        return {file.path for file in files} & self._too_large

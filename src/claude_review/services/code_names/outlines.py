"""The names outlining the files of a review's trees: each content outlined once, and a search never behind another.

What outlines a file follows from its path's language and its content
alone, and git names each content by an id it gives without reading it, so
an outline kept by both never goes stale. It is kept across reviews
(`OutlinesKept`): a file is parsed once for as long as nobody changes it.
What is not kept yet is parsed in a pool of processes, a chunk of files at
a time, as one interpreter parses 724 files in 0.8 s and four processes in
0.34 s, while threads, which tree-sitter holds the interpreter in, do no
better than one. The files a search waits for go to the front of what is
waiting to be parsed, so a search for a rare name is never behind one for a
frequent word, nor behind the whole tree being made ready ahead of the
reader's first search; and a search answers with what is outlined so far
when the rest takes longer than it waits.
"""

import asyncio
import hashlib
import importlib.metadata
from collections.abc import Coroutine
from concurrent.futures import Executor
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path, PurePosixPath
from types import ModuleType

import structlog
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from claude_review.domain import code_names
from claude_review.domain.interfaces import GitError, OutlinesKept, TreesRead
from claude_review.services.code_names import languages, reading
from claude_review.services.code_names.languages import code_files_of
from claude_review.services.code_names.reading import OutlinedName, outline

log = structlog.get_logger()

# How many files one process outlines at a time: few enough that a search asked meanwhile soon has a process free,
# enough that handing them over costs little beside parsing them
FILES_A_CHUNK = 32
# What a file only made ready is waited for by: no search, so after every file one waits for
NO_SEARCH = 0

# What decides the names outlining a file: the code that reads them, and the grammars it reads with. An outline
# kept under another generation was read by other code, and is never read back
OUTLINED_BY: list[ModuleType] = [reading, languages, code_names]
GRAMMARS = [
    "tree-sitter",
    "tree-sitter-python",
    "tree-sitter-javascript",
    "tree-sitter-typescript",
    "tree-sitter-svelte",
]
GENERATION_DIGEST_BYTES = 8

# The names outlining one file; None where its parse was given up, so nothing can be said of what it outlines
type Outline = list[OutlinedName] | None
OUTLINE_KEPT_AS = TypeAdapter[Outline](list[OutlinedName] | None)


class NamesParsing(BaseModel):
    """How a review outlines files: the processes it parses in, how many there are, and where outlines are kept,
    apart for each generation of the code outlining them (`outlines_generation`)."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    executor: Executor
    workers: int
    kept: OutlinesKept


class FileHeld(BaseModel):
    """A file by its path and the id of its content: what its outline is known by."""

    model_config = ConfigDict(frozen=True)

    path: str
    object_id: str

    @property
    def kept_as(self) -> str:
        """The key its outline is kept under across reviews: of its content, read as its path's language reads it."""
        return f"{self.object_id}{PurePosixPath(self.path).suffix}"


class FileRead(BaseModel):
    """A file's path and content, as handed to a process to outline."""

    model_config = ConfigDict(frozen=True)

    path: str
    content: bytes


class FilesOutlined(BaseModel):
    """Files of a tree by path, each with the names outlining it, None where nothing can be said of them, and whether
    every file asked about is among them."""

    model_config = ConfigDict(frozen=True)

    outlined: dict[str, Outline]
    complete: bool

    def outline_of(self, path: str) -> Outline:
        """The names outlining a file: none where the tree holds no file at the path."""
        return self.outlined.get(path, [])


class FilesAsked(BaseModel):
    """What a search waits for: each file's outline on its way, by path, and the files too large to outline."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    outlines: dict[str, asyncio.Future[Outline]]
    too_large: frozenset[str]

    def so_far(self) -> FilesOutlined:
        """The files outlined by now.

        Raises:
            GitError: if git could not read a file outlined by now.
        """
        done = {path: outline for path, outline in self.outlines.items() if outline.done()}
        outlined = {path: outline.result() for path, outline in done.items()}
        return FilesOutlined(
            outlined=outlined | dict.fromkeys(self.too_large), complete=len(done) == len(self.outlines)
        )


class Outlines:
    """The names outlining the files of one repository's trees, each content outlined once."""

    def __init__(self, repository: TreesRead, root: Path, parsing: NamesParsing) -> None:
        self._repository = repository
        self._root = root
        self._parsing = parsing
        # Every file asked about, its outline done or on its way: whoever asks for it again waits for that
        self._outlines: dict[FileHeld, asyncio.Future[Outline]] = {}
        # Read and waiting to be parsed, in the order read
        self._waiting: dict[FileHeld, bytes] = {}
        # The files searches wait for, each by the last search waiting for it, counted from the first: a file the
        # last search waits for is parsed before any other, and one no search waits for after every one that is
        self._searches = 0
        self._wanted: dict[FileHeld, int] = {}
        # How many chunks the processes are outlining now
        self._chunks_parsed = 0
        # The work going on, held so the loop does not lose it
        self._running: set[asyncio.Task[None]] = set()

    async def of_files(self, tree: str, paths: list[str]) -> FilesOutlined:
        """These files of the tree, every one outlined.

        Raises:
            GitError: if git cannot read the tree.
        """
        asked = await self._asked(tree, paths, wanted=True)
        # Shielded: a request let go of leaves each outline to whoever else waits for it
        await asyncio.gather(*(asyncio.shield(outline) for outline in asked.outlines.values()))
        return asked.so_far()

    async def holding_text(self, tree: str, text: str, *, within_seconds: float) -> FilesOutlined:
        """The files of the tree whose grammar the review reads that hold a text anywhere, whatever its case, as
        many outlined as are by the time given.

        Raises:
            GitError: if git cannot read the tree.
        """
        holding = await self._repository.paths_with_text(self._root, tree, text)
        asked = await self._asked(tree, [path for path in holding if code_files_of(path) is not None], wanted=True)
        if asked.outlines:
            # Waiting leaves the outlines it stops waiting for on their way
            await asyncio.wait(asked.outlines.values(), timeout=within_seconds)
        return asked.so_far()

    async def make_ready(self, tree: str) -> None:
        """Have every file of the tree outlined, behind whatever a search waits for.

        Raises:
            GitError: if git cannot list the tree.
        """
        paths = await self._repository.files_in(self._root, tree)
        await self._asked(tree, [path for path in sorted(paths) if code_files_of(path) is not None], wanted=False)

    async def _asked(self, tree: str, paths: list[str], *, wanted: bool) -> FilesAsked:
        """These files of the tree, each outline on its way: kept, being parsed, or now read to be; wanted, they are
        parsed before whatever else waits.

        Raises:
            GitError: if git cannot say what the tree holds at the paths.
        """
        at = await self._repository.blobs_at(self._root, tree, paths)
        held = {path: FileHeld(path=path, object_id=object_id) for path, object_id in at.object_ids.items()}
        if wanted:
            self._searches += 1
            self._wanted.update(dict.fromkeys(held.values(), self._searches))
        new = [file for file in held.values() if file not in self._outlines]
        loop = asyncio.get_running_loop()
        self._outlines.update((file, loop.create_future()) for file in new)
        if new:
            self._run(self._fetch(new))
        return FilesAsked(outlines={path: self._outlines[file] for path, file in held.items()}, too_large=at.too_large)

    async def _fetch(self, files: list[FileHeld]) -> None:
        """Take the outlines of these files from what is kept, and read the rest to be parsed."""
        kept = await self._parsing.kept.read([file.kept_as for file in files])
        unread = [file for file in files if not self._taken_from(kept.get(file.kept_as), file)]
        if not unread:
            return
        try:
            contents = await self._repository.blobs_read(self._root, [file.object_id for file in unread])
        except GitError as failed:
            for file in unread:
                self._outlines.pop(file).set_exception(failed)
            return
        self._waiting.update(zip(unread, contents, strict=True))
        self._feed()

    def _taken_from(self, kept: bytes | None, file: FileHeld) -> bool:
        """Whether the file's outline was kept and is taken from there: one kept by other code is not."""
        if kept is None:
            return False
        try:
            self._outlines[file].set_result(OUTLINE_KEPT_AS.validate_json(kept))
        except ValidationError:
            return False
        return True

    def _feed(self) -> None:
        """Hand the processes what waits, a chunk to each process free: what the last search waits for first."""
        while self._waiting and self._chunks_parsed < self._parsing.workers:
            # Sorted stably, so files no search tells apart keep the order they were read in
            by_search = sorted(self._waiting, key=lambda file: self._wanted.get(file, NO_SEARCH), reverse=True)
            chunk = by_search[:FILES_A_CHUNK]
            read = [FileRead(path=file.path, content=self._waiting.pop(file)) for file in chunk]
            for file in chunk:
                self._wanted.pop(file, None)
            self._chunks_parsed += 1
            self._run(self._parse(chunk, read))

    async def _parse(self, files: list[FileHeld], read: list[FileRead]) -> None:
        """Outline a chunk of files in a process, hand each its outline, and keep them for later reviews."""
        # Where the processes say nothing, a file has nothing that can be said of it: no search waits on it for ever
        outlines: list[Outline] = [None for _ in files]
        try:
            outlines = await asyncio.get_running_loop().run_in_executor(self._parsing.executor, _outlined, read)
        except BrokenProcessPool:
            log.exception("outline_process_died", files=len(files))
        finally:
            self._chunks_parsed -= 1
            for file, names in zip(files, outlines, strict=True):
                self._outlines[file].set_result(names)
            self._feed()
        await self._parsing.kept.keep(
            {file.kept_as: OUTLINE_KEPT_AS.dump_json(names) for file, names in zip(files, outlines, strict=True)}
        )

    def _run(self, work: Coroutine[None, None, None]) -> None:
        """Run work of its own, apart from the request that began it, holding it until it is done."""
        running = asyncio.create_task(work)
        self._running.add(running)
        running.add_done_callback(self._running.discard)


def outlines_generation() -> str:
    """A digest of what decides the names outlining a file: the code that reads them, and the grammars' versions."""
    digest = hashlib.blake2b(digest_size=GENERATION_DIGEST_BYTES)
    for module in OUTLINED_BY:
        digest.update(Path(str(module.__file__)).read_bytes())
    for grammar in GRAMMARS:
        digest.update(importlib.metadata.version(grammar).encode())
    return digest.hexdigest()


def _outlined(files: list[FileRead]) -> list[Outline]:
    """The names outlining each file, in the order given: run in a process of the pool."""
    return [outline(file.path, file.content) for file in files]

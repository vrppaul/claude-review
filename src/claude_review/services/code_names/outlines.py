"""The names outlining the files of a review's trees: each content outlined once ever, a search never behind another.

An outline follows from a file's language and content alone, and git names
each content by an id, so one kept by both never goes stale (`OutlinesKept`).
Parsing runs in processes, as tree-sitter holds the interpreter while it
parses, and what the last search waits for is parsed first.
"""

import asyncio
import hashlib
import heapq
import importlib.metadata
from collections.abc import Coroutine
from concurrent.futures import Executor
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path, PurePosixPath
from typing import Self

import structlog
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

import claude_review
from claude_review.domain.interfaces import GitError, OutlinesKept, TreesRead
from claude_review.services.code_names.languages import code_files_of
from claude_review.services.code_names.reading import OutlinedName, outline

log = structlog.get_logger()

# How many files one process outlines at a time: few enough that a search asked meanwhile soon has a process free,
# enough that handing them over costs little beside parsing them
FILES_A_CHUNK = 32
# What a file only made ready is waited for by: no search, so after every file one waits for
NO_SEARCH = 0
# The distributions whose grammars read the code, by the prefix of their names
GRAMMARS_PREFIX = "tree-sitter"
GENERATION_DIGEST_BYTES = 8

# The names outlining one file; None where its parse was given up, so nothing can be said of what it outlines
type Outline = list[OutlinedName] | None
OUTLINE_KEPT_AS = TypeAdapter[list[OutlinedName]](list[OutlinedName])


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


class Queued(BaseModel):
    """A file waiting to be parsed: by the last search waiting for it, then by when it was read."""

    model_config = ConfigDict(frozen=True)

    search: int
    read_at: int
    file: FileHeld

    def __lt__(self, other: Self) -> bool:
        """Whether it is parsed first: waited for by a later search, or read sooner."""
        if self.search != other.search:
            return self.search > other.search
        return self.read_at < other.read_at


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
        # Read and waiting to be parsed, each queued by what waits for it; an entry outdated by a later search is
        # passed over when it comes up
        self._waiting: dict[FileHeld, bytes] = {}
        self._queue: list[Queued] = []
        self._read_count = 0
        # The files searches wait for and are not outlined yet, each by the last search waiting, counted from one
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
        new = [file for file in held.values() if file not in self._outlines]
        loop = asyncio.get_running_loop()
        self._outlines.update((file, loop.create_future()) for file in new)
        if wanted:
            self._searches += 1
            for file in held.values():
                if not self._outlines[file].done():
                    self._wanted[file] = self._searches
                    self._queue_if_waiting(file)
        if new:
            self._run(self._fetch(new))
        return FilesAsked(outlines={path: self._outlines[file] for path, file in held.items()}, too_large=at.too_large)

    async def _fetch(self, files: list[FileHeld]) -> None:
        """Take the outlines of these files from what is kept, and read the rest to be parsed."""
        kept = await self._parsing.kept.read([file.kept_as for file in files])
        unread = [file for file in files if not self._set_from_kept(kept.get(file.kept_as), file)]
        if not unread:
            return
        try:
            contents = await self._repository.blobs_read(self._root, [file.object_id for file in unread])
        except GitError as failed:
            for file in unread:
                self._wanted.pop(file, None)
                self._outlines.pop(file).set_exception(failed)
            return
        for file, content in zip(unread, contents, strict=True):
            self._waiting[file] = content
            self._queue_if_waiting(file)
        self._feed()

    def _set_from_kept(self, kept: bytes | None, file: FileHeld) -> bool:
        """Set a file's outline from what was kept of it, and say whether it was: not where nothing was, or what was
        kept is in a form this code does not read."""
        if kept is None:
            return False
        try:
            names = OUTLINE_KEPT_AS.validate_json(kept)
        except ValidationError:
            return False
        self._wanted.pop(file, None)
        self._outlines[file].set_result(names)
        return True

    def _queue_if_waiting(self, file: FileHeld) -> None:
        """Queue a file waiting to be parsed by the last search waiting for it."""
        if file in self._waiting:
            self._read_count += 1
            queued = Queued(search=self._wanted.get(file, NO_SEARCH), read_at=self._read_count, file=file)
            heapq.heappush(self._queue, queued)

    def _feed(self) -> None:
        """Hand the processes what waits, a chunk to each process free: what the last search waits for first."""
        while self._waiting and self._chunks_parsed < self._parsing.workers:
            chunk: list[FileHeld] = []
            read: list[FileRead] = []
            while self._queue and len(chunk) < FILES_A_CHUNK:
                queued = heapq.heappop(self._queue)
                # Passed over: taken already, or queued again since by a later search
                if queued.file in self._waiting and self._wanted.get(queued.file, NO_SEARCH) == queued.search:
                    chunk.append(queued.file)
                    read.append(FileRead(path=queued.file.path, content=self._waiting.pop(queued.file)))
                    self._wanted.pop(queued.file, None)
            if not chunk:
                return
            self._chunks_parsed += 1
            self._run(self._parse(chunk, read))

    async def _parse(self, files: list[FileHeld], read: list[FileRead]) -> None:
        """Outline a chunk of files in a process, hand each its outline, and keep those outlined for later reviews."""
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
        # A file nothing could be said of, given up or lost with its process, is outlined again by a later review
        await self._parsing.kept.keep(
            {
                file.kept_as: OUTLINE_KEPT_AS.dump_json(names)
                for file, names in zip(files, outlines, strict=True)
                if names is not None
            }
        )

    def _run(self, work: Coroutine[None, None, None]) -> None:
        """Run work of its own, apart from the request that began it, holding it until it is done."""
        running = asyncio.create_task(work)
        self._running.add(running)
        running.add_done_callback(self._running.discard)


def outlines_generation() -> str:
    """A digest of all that can decide the names outlining a file: the review's own code and every grammar's version."""
    digest = hashlib.blake2b(digest_size=GENERATION_DIGEST_BYTES)
    package = Path(str(claude_review.__file__)).parent
    for source in sorted(package.rglob("*.py")):
        digest.update(source.read_bytes())
    grammars = sorted(
        f"{distribution.name}=={distribution.version}"
        for distribution in importlib.metadata.distributions()
        if distribution.name.startswith(GRAMMARS_PREFIX)
    )
    digest.update("\n".join(grammars).encode())
    return digest.hexdigest()


def _outlined(files: list[FileRead]) -> list[Outline]:
    """The names outlining each file, in the order given: run in a process of the pool."""
    return [outline(file.path, file.content) for file in files]

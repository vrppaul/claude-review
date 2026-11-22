"""The names outlining the files of a review's trees: each content outlined once ever, a search never behind another.

An outline follows from a file's language and content alone, and git names
each content by an id, so one kept by both never goes stale (`OutlinesKept`).
Parsing runs in processes, as tree-sitter holds the interpreter while it
parses, and what the last search waits for is parsed first. Once every file
of a tree is outlined, a search of it reads what is in memory alone.
"""

import asyncio
import hashlib
import importlib.metadata
from collections import deque
from collections.abc import Coroutine
from concurrent.futures import Executor
from concurrent.futures.process import BrokenProcessPool
from contextlib import suppress
from itertools import batched
from pathlib import Path

import structlog
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

import claude_review
from claude_review.domain.interfaces import GitError, OutlinesKept, TreesRead
from claude_review.domain.models import BlobsAt
from claude_review.services.code_names.languages import code_files_of, extension_of
from claude_review.services.code_names.reading import OutlinedName, outline

log = structlog.get_logger()

# How many files one process outlines at a time: few enough that a search asked meanwhile soon has a process free,
# enough that handing them over costs little beside parsing them
FILES_A_CHUNK = 32
# How many kept outlines are read back at a time: a search waits for no more than these of what a large tree kept,
# and the loop hands each piece out in some milliseconds
KEPT_READ_AT_ONCE = 500
# How many files a search marks as wanted at a time before the loop answers anything else
WANTED_AT_ONCE = 2000
# What a file only made ready is waited for by: no search, so after every file one waits for
NO_SEARCH = 0
# A search's files too large to outline: none it needs to name, as they outline no name it could find
NONE_TOO_LARGE: frozenset[str] = frozenset()
# The distributions whose grammars read the code, by the prefix of their names
GRAMMARS_PREFIX = "tree-sitter"
GENERATION_DIGEST_BYTES = 8

OUTLINE_KEPT_AS = TypeAdapter[list[OutlinedName]](list[OutlinedName])
# What stands between two names lower-cased: no name holds it
NAMES_APART = "\n"


class HeldOutline(BaseModel):
    """The names outlining a file, held in the form they are kept in, each name beside it as a search matches it."""

    model_config = ConfigDict(frozen=True)

    # A name becomes a model only where one is asked for: a large tree's tens of thousands held as models give the
    # collector hundreds of thousands of objects to walk, the loop waiting while it does
    kept: bytes
    names: list[str]
    # Each name lower-cased, as the tree's filter matches names, and all of them together, one to a line: a file
    # holding none of a text is passed over in one look
    lowered: list[str]
    lowered_together: str

    @classmethod
    def of(cls, outlining: list[OutlinedName]) -> HeldOutline:
        """The names a parse outlined, made ready to keep."""
        return cls._held(OUTLINE_KEPT_AS.dump_json(outlining), outlining)

    @classmethod
    def read_back(cls, kept: bytes) -> HeldOutline:
        """The names kept for a file, read back.

        Raises:
            ValidationError: if they were kept in a form this code does not read.
        """
        return cls._held(kept, OUTLINE_KEPT_AS.validate_json(kept))

    @classmethod
    def _held(cls, kept: bytes, outlining: list[OutlinedName]) -> HeldOutline:
        """The names as kept, each read out beside them."""
        names = [name.name for name in outlining]
        lowered = [name.lower() for name in names]
        return cls(kept=kept, names=names, lowered=lowered, lowered_together=NAMES_APART.join(lowered))

    def outlining(self) -> list[OutlinedName]:
        """Every name, as a model."""
        return OUTLINE_KEPT_AS.validate_json(self.kept)


# The names outlining one file; None where its parse was given up, so nothing can be said of what it outlines
type Outline = HeldOutline | None


class NamesParsing(BaseModel):
    """How a review outlines files: the processes it parses in, how many there are, and where outlines are kept,
    apart for each generation of the code outlining them (`outlines_generation`)."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    executor: Executor
    workers: int
    kept: OutlinesKept


class SearchWaits(BaseModel):
    """How long a search waits for the files it needs outlined before it answers with those outlined so far: asked
    a text first, and asked it again while it is not whole."""

    model_config = ConfigDict(frozen=True)

    first_seconds: float
    again_seconds: float


class FileHeld(BaseModel):
    """A file by its path and the id of its content, and what its outline is known by."""

    model_config = ConfigDict(frozen=True)

    path: str
    object_id: str
    # Its content read as its path's language reads it: one outline for every file holding the same, in the review
    # and in what is kept across reviews. A string, hashed once however often a search looks it up
    key: str

    @classmethod
    def at(cls, path: str, object_id: str) -> FileHeld:
        """A file of a tree, by its path and its content's id."""
        return cls(path=path, object_id=object_id, key=f"{object_id}{extension_of(path)}")


class CodeOfTree(BaseModel):
    """The files of a tree a grammar reads and the review outlines, in the order of their paths: none too large to
    read."""

    model_config = ConfigDict(frozen=True)

    tree: str
    files: list[FileHeld]

    @classmethod
    def of(cls, tree: str, blobs: BlobsAt) -> CodeOfTree:
        """Of every file a tree holds, those a grammar reads."""
        return cls(
            tree=tree,
            files=[
                FileHeld.at(path, object_id)
                for path, object_id in sorted(blobs.object_ids.items())
                if code_files_of(path) is not None
            ],
        )


class TextSought(BaseModel):
    """The files of a tree's code that git says hold a text, in the order of their paths."""

    model_config = ConfigDict(frozen=True)

    tree: str
    text: str
    files: list[FileHeld]


class FileRead(BaseModel):
    """A file's path and content, as handed to a process to outline."""

    model_config = ConfigDict(frozen=True)

    path: str
    content: bytes


class FilesOutlined(BaseModel):
    """Files of a tree by path, in the order asked, each with the names outlining it, None where nothing can be said
    of them, and whether every file asked about is among them."""

    model_config = ConfigDict(frozen=True)

    outlined: dict[str, Outline]
    complete: bool

    def outline_of(self, path: str) -> list[OutlinedName] | None:
        """The names outlining a file: none where the tree holds no file at the path, None where nothing can be said
        of it."""
        if path not in self.outlined:
            return []
        held = self.outlined[path]
        return None if held is None else held.outlining()


class FilesAsked(BaseModel):
    """What a caller waits for: each file's outline on its way, by path, and the files too large to outline."""

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


class NamesOfTree(BaseModel):
    """Every file of a tree outlined, once every one is: what a search of it reads from then on."""

    model_config = ConfigDict(frozen=True)

    tree: str
    outlined: FilesOutlined


class Outlines:
    """The names outlining the files of one repository's trees, each content outlined once."""

    def __init__(self, repository: TreesRead, root: Path, parsing: NamesParsing) -> None:
        self._repository = repository
        self._root = root
        self._parsing = parsing
        # Every content asked about, by its key, its outline done or on its way: whoever asks again waits for that
        self._outlines: dict[str, asyncio.Future[Outline]] = {}
        # Contents waiting to be read and parsed, by key, each as one file holding it, and their keys queued in turn
        # under the search waiting for them: the last search's first. A key queued again under a later search is
        # passed over where it was queued before
        self._waiting: dict[str, FileHeld] = {}
        self._queues: dict[int, deque[str]] = {}
        # The contents searches wait for and are not outlined yet, each by the last search waiting, counted from one
        self._searches = 0
        self._wanted: dict[str, int] = {}
        # How many chunks are being read and outlined now
        self._chunks_parsed = 0
        # The last tree listed whole, and the last text sought in one: the reader searches the take on screen, and
        # asks again for the same text until every file holding it is outlined
        self._listed: CodeOfTree | None = None
        self._sought: TextSought | None = None
        # Done once the files the last text sought waited for, when it was first asked, are outlined
        self._sought_outlined: asyncio.Future[list[Outline | BaseException]] | None = None
        # Every file of the last tree listed, once each is outlined
        self._whole: NamesOfTree | None = None
        # The work going on, held so the loop does not lose it
        self._running: set[asyncio.Task[None]] = set()

    async def of_files(self, tree: str, paths: list[str]) -> FilesOutlined:
        """These files of the tree, every one outlined.

        Raises:
            GitError: if git cannot read the tree.
        """
        at = await self._repository.blobs_at(self._root, tree, paths)
        files = [FileHeld.at(path, object_id) for path, object_id in at.object_ids.items()]
        asked = FilesAsked(outlines=self._asked(files), too_large=at.too_large)
        await self._want(files)
        # Shielded: a request let go of leaves each outline to whoever else waits for it
        await asyncio.gather(*(asyncio.shield(outline) for outline in asked.outlines.values()))
        return asked.so_far()

    async def holding_text(self, tree: str, text: str, *, waits: SearchWaits) -> FilesOutlined:
        """The files of the tree that may hold a text, whatever its case, in the order of their paths, as many
        outlined as are by the time it waits: every file of a grammar the review reads where all of them are
        outlined, else those git says hold it.

        Raises:
            GitError: if git cannot read the tree.
        """
        code = await self._code_of(tree)
        whole = self._whole_of(code)
        if whole is not None:
            return whole
        last_sought = self._sought
        sought = await self._holding(code, text)
        asked = self._asked(sought.files)
        # Asked again for the same text, the files it waits for are queued already, and one wait stands for them all
        asked_again = sought is last_sought and self._sought_outlined is not None
        if not asked_again:
            await self._want(sought.files)
            # Gathered once for every asking of the text: waiting on thousands of outlines each time costs the loop
            # tens of milliseconds
            self._sought_outlined = asyncio.gather(
                *(outline for outline in asked.values() if not outline.done()), return_exceptions=True
            )
        if self._sought_outlined is not None and not self._sought_outlined.done():
            # Waiting leaves the outlines it stops waiting for on their way
            await asyncio.wait(
                {self._sought_outlined}, timeout=waits.again_seconds if asked_again else waits.first_seconds
            )
        return FilesAsked(outlines=asked, too_large=NONE_TOO_LARGE).so_far()

    async def make_ready(self, tree: str) -> None:
        """Have every file of the tree outlined, behind whatever a search waits for.

        Raises:
            GitError: if git cannot list the tree.
        """
        code = await self._code_of(tree)
        self._asked(code.files)

    async def _code_of(self, tree: str) -> CodeOfTree:
        """The files of a tree a grammar reads, listed once for as long as it is the last tree listed.

        Raises:
            GitError: if git cannot list the tree.
        """
        listed = self._listed
        if listed is not None and listed.tree == tree:
            return listed
        blobs = await self._repository.blobs_in(self._root, tree)
        # Off the loop: a large tree holds tens of thousands of files
        listed = await asyncio.to_thread(CodeOfTree.of, tree, blobs)
        self._listed = listed
        return listed

    async def _holding(self, code: CodeOfTree, text: str) -> TextSought:
        """The files of a tree a grammar reads that hold a text, as git said for the last text sought, or says now.

        Raises:
            GitError: if git cannot search the tree.
        """
        sought = self._sought
        if sought is not None and sought.tree == code.tree and sought.text == text:
            return sought
        holding = frozenset(await self._repository.paths_with_text(self._root, code.tree, text))
        sought = TextSought(tree=code.tree, text=text, files=[file for file in code.files if file.path in holding])
        self._sought = sought
        return sought

    def _whole_of(self, code: CodeOfTree) -> FilesOutlined | None:
        """Every file of a tree outlined, gathered once each is, so a search of it needs nothing of git; None until
        then."""
        whole = self._whole
        if whole is not None and whole.tree == code.tree:
            return whole.outlined
        # A file git failed to read is asked about anew: a tree holding one is not whole until that file is read
        if not all((outline := self._outlines.get(file.key)) is not None and outline.done() for file in code.files):
            return None
        outlined = FilesAsked(outlines=self._held(code.files), too_large=NONE_TOO_LARGE).so_far()
        self._whole = NamesOfTree(tree=code.tree, outlined=outlined)
        return outlined

    def _asked(self, files: list[FileHeld]) -> dict[str, asyncio.Future[Outline]]:
        """These files' outlines by path, each on its way: kept, being parsed, or now queued to be."""
        new = {file.key: file for file in files if file.key not in self._outlines}
        loop = asyncio.get_running_loop()
        self._outlines.update((key, loop.create_future()) for key in new)
        if new:
            self._run(self._fetch(list(new.values())))
        return self._held(files)

    async def _want(self, files: list[FileHeld]) -> None:
        """Have these files parsed before whatever else waits, a piece at a time, as a search of a large tree's every
        file wants tens of thousands."""
        self._searches += 1
        search = self._searches
        for piece in batched(files, WANTED_AT_ONCE, strict=False):
            for file in piece:
                # A later search, asked while this one gave the loop its turn, keeps the files it wants first
                if not self._outlines[file.key].done() and self._wanted.get(file.key, NO_SEARCH) < search:
                    self._wanted[file.key] = search
                    self._queue_if_waiting(file.key)
            # The loop's turn: other requests are answered between pieces
            await asyncio.sleep(0)

    def _held(self, files: list[FileHeld]) -> dict[str, asyncio.Future[Outline]]:
        """The outlines of files asked about already, done or on their way, by path, in the order of the files."""
        return {file.path: self._outlines[file.key] for file in files}

    async def _fetch(self, files: list[FileHeld]) -> None:
        """Take the outlines of these contents from what is kept, and queue the rest to be read and parsed, a piece
        at a time, so each is waited for no longer than its own piece is read."""
        for piece in batched(files, KEPT_READ_AT_ONCE, strict=False):
            kept = await self._parsing.kept.read([file.key for file in piece])
            # Off the loop: kept outlines take the interpreter a while to read back
            read_back = await asyncio.to_thread(_read_back, kept) if kept else {}
            for file in piece:
                held = read_back.get(file.key)
                if held is None:
                    self._waiting[file.key] = file
                    self._queue_if_waiting(file.key)
                else:
                    self._wanted.pop(file.key, None)
                    self._outlines[file.key].set_result(held)
            self._feed()

    def _queue_if_waiting(self, key: str) -> None:
        """Queue a content waiting to be parsed under the last search waiting for it."""
        if key in self._waiting:
            self._queues.setdefault(self._wanted.get(key, NO_SEARCH), deque()).append(key)

    def _feed(self) -> None:
        """Hand the processes what waits, a chunk to each process free: what the last search waits for first."""
        while self._waiting and self._chunks_parsed < self._parsing.workers:
            chunk: list[FileHeld] = []
            while self._queues and len(chunk) < FILES_A_CHUNK:
                search = max(self._queues)
                queued = self._queues[search]
                key = queued.popleft()
                if not queued:
                    del self._queues[search]
                # Passed over: taken already, or queued again since by a later search
                if key in self._waiting and self._wanted.get(key, NO_SEARCH) == search:
                    chunk.append(self._waiting.pop(key))
                    self._wanted.pop(key, None)
            if not chunk:
                return
            self._chunks_parsed += 1
            self._run(self._parse(chunk))

    async def _parse(self, files: list[FileHeld]) -> None:
        """Read a chunk of files, outline them in a process, hand each its outline, and keep those outlined for
        later reviews."""
        # Where the processes say nothing, a file has nothing that can be said of it: no caller waits on it for ever
        outlines: list[Outline] = [None for _ in files]
        unread: GitError | None = None
        try:
            outlines = await self._outlined(files)
        except GitError as failed:
            unread = failed
        finally:
            # A process is free for the next chunk, whatever came of this one
            self._chunks_parsed -= 1
            self._settle(files, outlines, unread)
            self._feed()
        if unread is not None:
            return
        # A file nothing could be said of, given up or lost with its process, is outlined again by a later review
        await self._parsing.kept.keep(
            {file.key: held.kept for file, held in zip(files, outlines, strict=True) if held is not None}
        )

    async def _outlined(self, files: list[FileHeld]) -> list[Outline]:
        """The names outlining each of a chunk of files, read only now, so the review holds no more of the tree than
        its processes are outlining.

        Raises:
            GitError: if git cannot read a file.
        """
        contents = await self._repository.blobs_read(self._root, [file.object_id for file in files])
        read = [FileRead(path=file.path, content=content) for file, content in zip(files, contents, strict=True)]
        try:
            outlinings = await asyncio.get_running_loop().run_in_executor(self._parsing.executor, _outlines_of, read)
        except BrokenProcessPool:
            log.exception("outline_process_died", files=len(files))
            return [None for _ in files]
        return [None if outlining is None else HeldOutline.of(outlining) for outlining in outlinings]

    def _settle(self, files: list[FileHeld], outlines: list[Outline], unread: GitError | None) -> None:
        """Hand each of a chunk of files its outline, or, where git could not read them, the failure: a file
        that failed is asked about anew by whoever asks next."""
        for file, held in zip(files, outlines, strict=True):
            if unread is None:
                self._outlines[file.key].set_result(held)
            else:
                self._outlines.pop(file.key).set_exception(unread)

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


def _read_back(kept: dict[str, bytes]) -> dict[str, HeldOutline]:
    """The outlines kept under each key, read back; one kept in a form this code does not read is left out."""
    read_back: dict[str, HeldOutline] = {}
    for key, outline_kept in kept.items():
        with suppress(ValidationError):
            read_back[key] = HeldOutline.read_back(outline_kept)
    return read_back


def _outlines_of(files: list[FileRead]) -> list[list[OutlinedName] | None]:
    """The names outlining each file, in the order given: run in a process of the pool."""
    return [outline(file.path, file.content) for file in files]

"""The names outlining the files of a review's trees, kept by what each file holds, so a file is read and parsed once.

What outlines a file follows from its path's language and its content
alone, and git names each content by an id it gives without reading it. One
kept by both never goes stale: a round reads only the files it rewrote, and
the tree's filter, asked at each pause in typing, reads each file once.
Parsing all 724 files of this repository takes 1.4 s; asking their ids, a
few milliseconds. What is kept lives as long as the review and grows only by
the files its rounds rewrite.
"""

import asyncio
from functools import partial
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from claude_review.domain.interfaces import TreesRead
from claude_review.services.code_names.languages import code_files_of
from claude_review.services.code_names.reading import OutlinedName, outline


class FileHeld(BaseModel):
    """A file by its path and the id of its content: what its outline is kept by."""

    model_config = ConfigDict(frozen=True)

    path: str
    object_id: str


# Files read in one asking, each with the names outlining it, None where its parse was given up
type FilesParsed = dict[FileHeld, list[OutlinedName] | None]


class FilesOutlined(BaseModel):
    """Files of a tree by path, each with the names outlining it; None where the file was too large to read or its
    parse was given up, so nothing can be said of what it outlines."""

    model_config = ConfigDict(frozen=True)

    outlined: dict[str, list[OutlinedName] | None]

    def outline_of(self, path: str) -> list[OutlinedName] | None:
        """The names outlining a file: none where the tree holds no file at the path."""
        return self.outlined.get(path, [])


class Outlines:
    """The names outlining the files of one repository's trees, kept by what each file holds."""

    def __init__(self, repository: TreesRead, root: Path) -> None:
        self._repository = repository
        self._root = root
        # Each file's reading, done or on its way, by the file: whoever asks for a file being read waits for that
        # reading rather than starting another. A file whose parse was given up is kept as such: it would be given
        # up again
        self._kept: dict[FileHeld, asyncio.Task[FilesParsed]] = {}

    async def of_files(self, tree: str, paths: list[str]) -> FilesOutlined:
        """These files of the tree, outlined: only those no file of the path held the same content of before are read.

        Raises:
            GitError: if git cannot read the tree.
        """
        at = await self._repository.blobs_at(self._root, tree, paths)
        held = {path: FileHeld(path=path, object_id=object_id) for path, object_id in at.object_ids.items()}
        unread = [file for file in held.values() if file not in self._kept]
        if unread:
            reading = asyncio.create_task(self._read(unread))
            reading.add_done_callback(partial(self._forget_if_failed, unread))
            self._kept.update(dict.fromkeys(unread, reading))
        # Taken before any is waited for: a reading that fails meanwhile is forgotten, and its failure is git's
        readings = {path: self._kept[file] for path, file in held.items()}
        # Shielded: a request let go of leaves the reading to whoever else waits for it
        outlined = {path: (await asyncio.shield(readings[path]))[file] for path, file in held.items()}
        return FilesOutlined(outlined=outlined | dict.fromkeys(at.too_large))

    async def holding_text(self, tree: str, text: str) -> FilesOutlined:
        """The files of the tree whose grammar the review reads that hold a text anywhere, whatever its case, outlined.

        Raises:
            GitError: if git cannot read the tree.
        """
        holding = await self._repository.paths_with_text(self._root, tree, text)
        return await self.of_files(tree, [path for path in holding if code_files_of(path) is not None])

    async def _read(self, files: list[FileHeld]) -> FilesParsed:
        """Read these files' contents and outline each.

        Raises:
            GitError: if git cannot read them.
        """
        contents = await self._repository.blobs_read(self._root, [file.object_id for file in files])
        return await asyncio.to_thread(_parsed, dict(zip(files, contents, strict=True)))

    def _forget_if_failed(self, files: list[FileHeld], reading: asyncio.Task[FilesParsed]) -> None:
        """Forget a reading that failed, so the next to ask for its files reads them again."""
        if reading.cancelled() or reading.exception() is not None:
            for file in files:
                del self._kept[file]


def _parsed(contents: dict[FileHeld, bytes]) -> FilesParsed:
    """The names outlining each file, read by its grammar: the CPU's work, done off the event loop."""
    return {file: outline(file.path, content) for file, content in contents.items()}

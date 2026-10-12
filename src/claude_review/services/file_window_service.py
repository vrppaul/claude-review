"""Service for reading a window of lines out of a file in the repository.

Expanding the context around a hunk means asking for lines the diff left
out. The browser names the path, so this is the one place the review server
opens a file it was not told about up front — hence the checks below.
"""

import asyncio
from itertools import islice
from pathlib import Path
from typing import BinaryIO

from pydantic import BaseModel

from claude_review.domain.exceptions import (
    FileNotInReviewError,
    FileUnreadableError,
    LineRangeError,
    PathOutsideRepositoryError,
)
from claude_review.domain.interfaces import TrackedPaths
from claude_review.domain.models import FIRST_LINE

MAX_WINDOW_LINES = 2000

# Reading a window used to load the whole file, so expanding context over a
# lock file or a generated bundle stalled the server for seconds and took
# hundreds of megabytes. Nothing a person reads is anywhere near this.
MAX_FILE_BYTES = 32 * 1024 * 1024

# How git tells a binary file from text: a NUL byte among the first it reads
BINARY_CHECK_BYTES = 8000
BINARY_MARK = b"\0"
# What ends a line, and nothing else does: git numbers a file's lines by it,
# so a lone carriage return is part of the line it is in
LINE_END = b"\n"
# What a file's bytes are read as; a byte that is not is replaced, as the diff
# shows it, rather than the file refused
TEXT_ENCODING = "utf-8"
NOT_TEXT = "replace"


class FileWindow(BaseModel):
    """A run of lines from a file, and how long the file is."""

    start: int
    lines: list[str]
    total: int


class FileWindowService:
    """Reads line ranges out of files inside one repository."""

    def __init__(self, repository: TrackedPaths) -> None:
        self._repository = repository

    async def read_window(
        self,
        root: Path,
        relative_path: str,
        start: int,
        end: int,
        *,
        in_review: frozenset[str],
    ) -> FileWindow:
        """Read lines ``start`` to ``end`` inclusive, counting from one.

        A window running past the end of the file is clamped rather than
        refused, since the caller cannot know the length before asking.

        Only a file the review holds, or one the repository tracks, can be
        read. Read against another base, the diff on screen holds files the
        review's own does not; but nothing the repository leaves out — a
        `.env`, a build directory — is ever a file the reader widens.

        Raises:
            LineRangeError: if the range runs backwards or below line one.
            PathOutsideRepositoryError: if the path does not name a place
                inside the repository.
            FileNotInReviewError: if the review neither holds nor tracks the
                file, or nothing readable is there.
            FileUnreadableError: if the file is not text, or too large to read.
        """
        if start < FIRST_LINE or end < start:
            msg = f"not a line range: {start}-{end}"
            raise LineRangeError(msg)

        # Resolving links and reading both block, and the server has a socket
        # to keep answering on. A path that leaves the repository is refused
        # as that, before anything is asked about the file it names.
        await asyncio.to_thread(self._check_inside, root, relative_path)

        if relative_path not in in_review and not await self._repository.is_tracked(root, relative_path):
            msg = f"not a file in this review: {relative_path}"
            raise FileNotInReviewError(msg)

        return await asyncio.to_thread(self._read_window, root / relative_path, relative_path, start, end)

    def _read_window(self, path: Path, named: str, start: int, end: int) -> FileWindow:
        """Read the wanted lines without holding the whole file in memory.

        Read as bytes and parted at line breaks alone, the way git numbers a
        file's lines, so the lines widened in beside a hunk are the very
        lines its numbers name.
        """
        self._check_readable(path, named)

        wanted = min(end - start + 1, MAX_WINDOW_LINES)
        try:
            with path.open("rb") as handle:
                is_text = BINARY_MARK not in handle.read(BINARY_CHECK_BYTES)
                window = _window_from(handle, start, wanted) if is_text else None
        except OSError as error:
            msg = f"cannot read: {named}"
            raise FileUnreadableError(msg) from error
        if window is None:
            msg = f"cannot read as text: {named}"
            raise FileUnreadableError(msg)
        return window

    def _check_readable(self, path: Path, named: str) -> None:
        # A link's one line is the name of what it points at, which the diff
        # already shows whole. Read through, it would widen into a file the
        # review need not hold — the ignored `.env` it points at.
        if path.is_symlink():
            msg = f"a link has no lines of its own to widen: {named}"
            raise FileUnreadableError(msg)
        if not path.is_file():
            msg = f"not a readable file: {named}"
            raise FileNotInReviewError(msg)
        if path.stat().st_size > MAX_FILE_BYTES:
            msg = f"too large to expand: {named}"
            raise FileUnreadableError(msg)

    def _check_inside(self, root: Path, relative_path: str) -> None:
        """Refuse a path that leaves the repository, wherever its links lead.

        Resolution follows symlinks, so a link pointing outside the tree is
        rejected along with "..", and the check is on the resolved path
        rather than the text of the request.
        """
        candidate = Path(relative_path)
        if candidate.is_absolute():
            msg = f"path must be relative to the repository: {relative_path}"
            raise PathOutsideRepositoryError(msg)

        try:
            resolved = (root / candidate).resolve()
            inside = resolved.is_relative_to(root.resolve())
        except (ValueError, OSError) as error:
            # A NUL byte, or a path the filesystem will not even look at
            msg = f"not a usable path: {relative_path}"
            raise PathOutsideRepositoryError(msg) from error

        if not inside:
            msg = f"path leaves the repository: {relative_path}"
            raise PathOutsideRepositoryError(msg)


def _window_from(handle: BinaryIO, start: int, wanted: int) -> FileWindow:
    """The wanted lines of a file read from its start, and how many lines it has in all."""
    handle.seek(0)
    # How many lines stand above the window
    above = start - FIRST_LINE
    window = [
        line.removesuffix(LINE_END).decode(TEXT_ENCODING, errors=NOT_TEXT)
        for line in islice(handle, above, above + wanted)
    ]
    return FileWindow(start=start, lines=window, total=above + len(window) + sum(1 for _ in handle))

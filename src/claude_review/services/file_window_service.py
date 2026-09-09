"""Service for reading a window of lines out of a file in the repository.

Expanding the context around a hunk means asking for lines the diff left
out. The browser names the path, so this is the one place the review server
opens a file it was not told about up front — hence the checks below.
"""

import asyncio
from collections.abc import Iterable
from itertools import islice
from pathlib import Path

from pydantic import BaseModel

from claude_review.domain.exceptions import FileWindowError

MAX_WINDOW_LINES = 2000

# Reading a window used to load the whole file, so expanding context over a
# lock file or a generated bundle stalled the server for seconds and took
# hundreds of megabytes. Nothing a person reads is anywhere near this.
MAX_FILE_BYTES = 32 * 1024 * 1024


class FileWindow(BaseModel):
    """A run of lines from a file, and how long the file is."""

    start: int
    lines: list[str]
    total: int


class FileWindowService:
    """Reads line ranges out of files inside one repository."""

    async def read_window(
        self,
        root: Path,
        relative_path: str,
        start: int,
        end: int,
        *,
        allowed: Iterable[str] | None = None,
    ) -> FileWindow:
        """Read lines ``start`` to ``end`` inclusive, counting from one.

        A window running past the end of the file is clamped rather than
        refused, since the caller cannot know the length before asking.

        ``allowed``, when given, is the set of paths the review covers. The
        UI never asks for anything else, and refusing the rest keeps the
        review from being a way to read the whole repository.

        Raises:
            FileWindowError: If the range is not sensible, or the path does
                not name a readable text file the review covers.
        """
        if start < 1 or end < start:
            msg = f"not a line range: {start}-{end}"
            raise FileWindowError(msg)

        if allowed is not None and relative_path not in set(allowed):
            msg = f"not a file in this review: {relative_path}"
            raise FileWindowError(msg)

        path = self._resolve_inside(root, relative_path)
        # Reading blocks, and the server has a socket to keep answering on
        return await asyncio.to_thread(self._read_window, path, relative_path, start, end)

    def _read_window(self, path: Path, named: str, start: int, end: int) -> FileWindow:
        """Read the wanted lines without holding the whole file in memory."""
        self._check_readable(path, named)

        wanted = min(end - start + 1, MAX_WINDOW_LINES)
        try:
            with path.open(encoding="utf-8") as handle:
                window = [line.rstrip("\n") for line in islice(handle, start - 1, start - 1 + wanted)]
                total = start - 1 + len(window) + sum(1 for _ in handle)
        except (OSError, UnicodeDecodeError) as e:
            msg = f"cannot read as text: {named}"
            raise FileWindowError(msg) from e

        return FileWindow(start=start, lines=window, total=total)

    def _check_readable(self, path: Path, named: str) -> None:
        if not path.is_file():
            msg = f"not a readable file: {named}"
            raise FileWindowError(msg)
        if path.stat().st_size > MAX_FILE_BYTES:
            msg = f"too large to expand: {named}"
            raise FileWindowError(msg)

    def _resolve_inside(self, root: Path, relative_path: str) -> Path:
        """Resolve a path and refuse anything that leaves the repository.

        Resolution follows symlinks, so a link pointing outside the tree is
        rejected along with "..", and the check is on the resolved path
        rather than the text of the request.
        """
        candidate = Path(relative_path)
        if candidate.is_absolute():
            msg = f"path must be relative to the repository: {relative_path}"
            raise FileWindowError(msg)

        try:
            resolved = (root / candidate).resolve()
            inside = resolved.is_relative_to(root.resolve())
        except (ValueError, OSError) as e:
            # A NUL byte, or a path the filesystem will not even look at
            msg = f"not a usable path: {relative_path}"
            raise FileWindowError(msg) from e

        if not inside:
            msg = f"path leaves the repository: {relative_path}"
            raise FileWindowError(msg)
        return resolved

"""Service for reading text files into reviewable DiffFile structures.

Text files are mapped into the existing DiffFile model so that the same
review UI, comment system, and submission pipeline work for both git diffs
and plain text files (plans, docs, etc.).
"""

import asyncio
from pathlib import Path

from claude_review.domain.models import DiffFile
from claude_review.services.unreadable_content import UnreadableContentError
from claude_review.services.whole_file import whole_file


class TextFileService:
    """Converts plain text files into DiffFile models for review."""

    async def read_files(self, paths: list[Path]) -> list[DiffFile]:
        """Read files and convert each into a reviewable DiffFile, on a thread rather than the event loop.

        The paths come resolved from whoever opens the review, so a file
        named twice is read once. Empty files are skipped.

        Raises:
            UnreadableContentError: If a path does not point to a readable text file.
        """
        return await asyncio.to_thread(self._read_all, paths)

    def _read_all(self, paths: list[Path]) -> list[DiffFile]:
        files: list[DiffFile] = []
        for path in dict.fromkeys(paths):
            text = self._read_text(path)
            if text:
                files.append(whole_file(self._display_path(path), text))
        return files

    def _display_path(self, path: Path) -> str:
        """Name a file the way the reader would.

        A path under the working directory reads as "docs/plan.md" rather
        than its full location; one outside it keeps the full path, since
        "../../elsewhere.md" would say less.
        """
        try:
            return str(path.relative_to(Path.cwd()))
        except ValueError:
            return str(path)

    def _read_text(self, path: Path) -> str:
        """Read file content as UTF-8 text.

        Raises:
            UnreadableContentError: If the path is missing, is a directory,
                cannot be read, or is not UTF-8 text.
        """
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            msg = f"Not a readable text file: {path}"
            raise UnreadableContentError(msg) from error

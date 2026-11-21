"""Files of the take on screen, read from the tree git wrote the take down as and never from the disk.

Read so, a file's lines are numbered as the diff's and the name lookup's
are, whatever was saved since the take, and nothing `.gitignore` shuts out
is ever read: no tree holds it.
"""

from pathlib import Path

from claude_review.domain.exceptions import FileNotInReviewError, FileUnreadableError, LineRangeError
from claude_review.domain.interfaces import TreesRead
from claude_review.domain.models import (
    FIRST_LINE,
    MAX_WINDOW_LINES,
    FileOfTake,
    FileWindow,
    OpenedFileOfTake,
    Unshown,
    UnshownFileOfTake,
    runs_backwards,
)
from claude_review.services.file_lines import is_text, line_text, lines_of
from claude_review.services.whole_file import whole_hunk


class FilesOfTake:
    """Reads files of the takes of one repository's review: whole, or the lines a hunk left out."""

    def __init__(self, repository: TreesRead, root: Path) -> None:
        self._repository = repository
        self._root = root

    async def file(self, tree: str, path: str) -> OpenedFileOfTake:
        """One file of the take written down as `tree`: whole, or saying why the review reads no lines of it.

        Raises:
            FileNotInReviewError: if the tree holds no file at the path.
        """
        held = await self._held_at(tree, path)
        if isinstance(held, Unshown):
            return UnshownFileOfTake(path=path, unshown=held)
        return FileOfTake(path=path, hunk=whole_hunk(held))

    async def window(self, tree: str, path: str, start: int, end: int) -> FileWindow:
        """Lines `start` to `end` of a file of the take, both among them, counted from one.

        A window running past the file's end stops there: whoever asks cannot
        know how long the file is before asking.

        Raises:
            LineRangeError: if the lines run backwards, or start below the first.
            FileNotInReviewError: if the tree holds no file at the path.
            FileUnreadableError: if the review reads no lines of the file: it is not text, or too large.
        """
        if start < FIRST_LINE or runs_backwards(start, end):
            msg = f"not a line range: {start}-{end}"
            raise LineRangeError(msg)
        held = await self._held_at(tree, path)
        if isinstance(held, Unshown):
            msg = f"the review reads no lines of {path}"
            raise FileUnreadableError(msg)
        lines = lines_of(held)
        above = start - FIRST_LINE
        wanted = min(end - start + 1, MAX_WINDOW_LINES)
        return FileWindow(
            start=start, lines=[line_text(line) for line in lines[above : above + wanted]], total=len(lines)
        )

    async def text_files(self, tree: str, paths: list[str]) -> list[FileOfTake]:
        """Those of these files of the take the review reads line by line, each whole, all in one asking."""
        read = await self._repository.files_of(self._root, tree, paths)
        return [
            FileOfTake(path=path, hunk=whole_hunk(content))
            for path, content in read.contents.items()
            if is_text(content)
        ]

    async def _held_at(self, tree: str, path: str) -> bytes | Unshown:
        """What a tree holds at a path: a file's bytes where the review reads its lines, or why it reads none.

        Raises:
            FileNotInReviewError: if the tree holds no file at the path.
        """
        read = await self._repository.files_of(self._root, tree, [path])
        if path in read.too_large:
            return Unshown.TOO_LARGE
        content = read.contents.get(path)
        if content is None:
            msg = f"no file of the take on screen at {path}"
            raise FileNotInReviewError(msg)
        return content if is_text(content) else Unshown.BINARY

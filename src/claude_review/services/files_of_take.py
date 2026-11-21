"""Files of the take on screen read whole, from the tree git wrote the take down as and never from the disk.

Read so, a file's lines are numbered as the diff's and the name lookup's
are, and nothing `.gitignore` shuts out is ever read: no tree holds it.
"""

from pathlib import Path

from claude_review.domain.exceptions import FileNotInReviewError
from claude_review.domain.interfaces import TreesRead
from claude_review.domain.models import FileOfTake, OpenedFileOfTake, Unshown, UnshownFileOfTake
from claude_review.services.file_lines import is_text
from claude_review.services.whole_file import whole_hunk


class FilesOfTake:
    """Reads files of the takes of one repository's review whole."""

    def __init__(self, repository: TreesRead, root: Path) -> None:
        self._repository = repository
        self._root = root

    async def file(self, tree: str, path: str) -> OpenedFileOfTake:
        """One file of the take written down as `tree`: whole, or saying why the review reads no lines of it.

        Raises:
            FileNotInReviewError: if the tree holds no file at the path.
        """
        read = await self._repository.files_of(self._root, tree, [path])
        if path in read.too_large:
            return UnshownFileOfTake(path=path, unshown=Unshown.TOO_LARGE)
        content = read.contents.get(path)
        if content is None:
            msg = f"no file of the take on screen at {path}"
            raise FileNotInReviewError(msg)
        if not is_text(content):
            return UnshownFileOfTake(path=path, unshown=Unshown.BINARY)
        return FileOfTake(path=path, hunk=whole_hunk(content))

    async def text_files(self, tree: str, paths: list[str]) -> list[FileOfTake]:
        """Those of these files of the take the review reads line by line, each whole, all in one asking."""
        read = await self._repository.files_of(self._root, tree, paths)
        return [
            FileOfTake(path=path, hunk=whole_hunk(content))
            for path, content in read.contents.items()
            if is_text(content)
        ]

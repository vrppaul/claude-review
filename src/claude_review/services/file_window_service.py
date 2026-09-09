"""Service for reading a window of lines out of a file in the repository.

Expanding the context around a hunk means asking for lines the diff left
out. The browser names the path, so this is the one place the review server
opens a file it was not told about up front — hence the checks below.
"""

from pathlib import Path

from pydantic import BaseModel

from claude_review.domain.exceptions import FileWindowError

MAX_WINDOW_LINES = 2000


class FileWindow(BaseModel):
    """A run of lines from a file, and how long the file is."""

    start: int
    lines: list[str]
    total: int


class FileWindowService:
    """Reads line ranges out of files inside one repository."""

    def read_window(self, root: Path, relative_path: str, start: int, end: int) -> FileWindow:
        """Read lines ``start`` to ``end`` inclusive, counting from one.

        A window running past the end of the file is clamped rather than
        refused, since the caller cannot know the length before asking.

        Raises:
            FileWindowError: If the range is not sensible, or the path does
                not name a readable text file inside ``root``.
        """
        if start < 1 or end < start:
            msg = f"not a line range: {start}-{end}"
            raise FileWindowError(msg)

        path = self._resolve_inside(root, relative_path)
        lines = self._read_lines(path)

        window = lines[start - 1 : min(end, start - 1 + MAX_WINDOW_LINES)]
        return FileWindow(start=start, lines=window, total=len(lines))

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

        resolved = (root / candidate).resolve()
        if not resolved.is_relative_to(root.resolve()):
            msg = f"path leaves the repository: {relative_path}"
            raise FileWindowError(msg)
        return resolved

    def _read_lines(self, path: Path) -> list[str]:
        if not path.is_file():
            msg = f"not a readable file: {path}"
            raise FileWindowError(msg)

        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            msg = f"cannot read as text: {e}"
            raise FileWindowError(msg) from e

        lines = text.split("\n")
        # A trailing newline ends the last line rather than starting a new one
        if lines and lines[-1] == "":
            lines.pop()
        return lines

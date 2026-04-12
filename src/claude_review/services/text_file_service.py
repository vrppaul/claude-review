"""Service for reading text files into reviewable DiffFile structures.

Text files are mapped into the existing DiffFile model so that the same
review UI, comment system, and submission pipeline work for both git diffs
and plain text files (plans, docs, etc.).  Every line becomes a CONTEXT
line with a single line number — there is no "old" vs "new" distinction.
"""

from pathlib import Path

from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, LineType


class TextFileService:
    """Converts plain text files into DiffFile models for review."""

    def read_files(self, paths: list[Path]) -> list[DiffFile]:
        """Read files and convert each into a reviewable DiffFile.

        Skips empty files.  Deduplicates paths so the same file
        is not loaded twice.

        Raises:
            FileNotFoundError: If a path does not point to a readable file.
        """
        seen: set[Path] = set()
        result: list[DiffFile] = []

        for path in paths:
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)

            text = self._read_text(resolved)
            if not text:
                continue

            lines = self._split_lines(text)
            result.append(self._build_diff_file(str(resolved), lines))

        return result

    def _read_text(self, path: Path) -> str:
        """Read file content as UTF-8 text.

        Raises:
            FileNotFoundError: If the path is missing, is a directory,
                or cannot be read.
        """
        if not path.is_file():
            msg = f"Not a readable file: {path}"
            raise FileNotFoundError(msg)
        return path.read_text(encoding="utf-8")

    def _split_lines(self, text: str) -> list[str]:
        """Split text into lines, stripping a single trailing empty line."""
        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        return lines

    def _build_diff_file(self, path: str, raw_lines: list[str]) -> DiffFile:
        """Wrap lines into a DiffFile with a single all-context hunk."""
        diff_lines = [
            DiffLine(type=LineType.CONTEXT, old_no=None, new_no=i, content=line)
            for i, line in enumerate(raw_lines, start=1)
        ]
        hunk = DiffHunk(
            header="",
            old_start=0,  # no "old" version for plain text
            new_start=1,
            lines=diff_lines,
        )
        return DiffFile(path=path, status=FileStatus.ADDED, hunks=[hunk])

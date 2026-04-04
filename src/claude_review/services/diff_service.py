"""Service for parsing git diffs into domain models."""

import re
from pathlib import Path

from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, LineType
from claude_review.domain.protocols import GitRepositoryProtocol


class DiffService:
    """Parses raw git diff output into structured domain models."""

    def __init__(self, git_repository: GitRepositoryProtocol) -> None:
        self._git = git_repository

    async def get_diff(self, path: Path) -> list[DiffFile]:
        """Get parsed diff for the given repository path."""
        raw = await self._git.get_raw_diff(path)
        if not raw.strip():
            return []
        return self._parse_diff(raw)

    def _parse_diff(self, raw: str) -> list[DiffFile]:
        """Parse unified diff output into DiffFile models."""
        files: list[DiffFile] = []
        file_chunks = re.split(r"^diff --git ", raw, flags=re.MULTILINE)

        for chunk in file_chunks:
            if not chunk.strip():
                continue

            file = self._parse_file_chunk(chunk)
            if file is not None:
                files.append(file)

        return files

    def _parse_file_chunk(self, chunk: str) -> DiffFile | None:
        """Parse a single file's diff chunk."""
        lines = chunk.split("\n")

        path = self._extract_path(lines[0])
        if path is None:
            return None

        status = self._detect_status(lines)
        hunks = self._parse_hunks(lines)

        return DiffFile(path=path, status=status, hunks=hunks)

    def _extract_path(self, header_line: str) -> str | None:
        """Extract file path from the diff header line."""
        # Header format: "a/path/to/file b/path/to/file"
        match = re.match(r"a/(.+?) b/(.+)", header_line)
        if match:
            return match.group(2)
        return None

    def _detect_status(self, lines: list[str]) -> FileStatus:
        """Detect file status from diff metadata lines."""
        for line in lines:
            if line.startswith("new file"):
                return FileStatus.ADDED
            if line.startswith("deleted file"):
                return FileStatus.DELETED
            if line.startswith("rename from"):
                return FileStatus.RENAMED
        return FileStatus.MODIFIED

    def _parse_hunks(self, lines: list[str]) -> list[DiffHunk]:
        """Parse all hunks from a file's diff lines."""
        hunks: list[DiffHunk] = []
        current_hunk_lines: list[str] = []
        current_header = ""
        old_start = 0
        new_start = 0

        for line in lines:
            hunk_match = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)", line)
            if hunk_match:
                # Save previous hunk
                if current_header:
                    hunks.append(self._build_hunk(current_header, old_start, new_start, current_hunk_lines))
                current_header = line
                old_start = int(hunk_match.group(1))
                new_start = int(hunk_match.group(2))
                current_hunk_lines = []
            elif current_header:
                current_hunk_lines.append(line)

        # Don't forget the last hunk
        if current_header:
            hunks.append(self._build_hunk(current_header, old_start, new_start, current_hunk_lines))

        return hunks

    def _build_hunk(self, header: str, old_start: int, new_start: int, raw_lines: list[str]) -> DiffHunk:
        """Build a DiffHunk from raw diff lines."""
        diff_lines: list[DiffLine] = []
        old_no = old_start
        new_no = new_start

        for line in raw_lines:
            if line.startswith("+"):
                diff_lines.append(DiffLine(type=LineType.ADD, old_no=None, new_no=new_no, content=line[1:]))
                new_no += 1
            elif line.startswith("-"):
                diff_lines.append(DiffLine(type=LineType.DELETE, old_no=old_no, new_no=None, content=line[1:]))
                old_no += 1
            elif line.startswith(" "):
                diff_lines.append(DiffLine(type=LineType.CONTEXT, old_no=old_no, new_no=new_no, content=line[1:]))
                old_no += 1
                new_no += 1
            elif line.startswith("\\"):
                # "\ No newline at end of file" — skip
                continue

        return DiffHunk(header=header, old_start=old_start, new_start=new_start, lines=diff_lines)

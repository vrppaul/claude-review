"""Service for parsing git diffs into domain models."""

import re
from pathlib import Path

from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, LineType
from claude_review.domain.protocols import GitRepositoryProtocol

# Git escapes these as two characters inside a quoted path
_CONTROL_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}


class DiffService:
    """Parses raw git diff output into structured domain models."""

    def __init__(self, git_repository: GitRepositoryProtocol) -> None:
        self._git = git_repository

    async def get_diff(
        self,
        path: Path,
        base: str | None = None,
        *,
        ignore_whitespace: bool = False,
    ) -> list[DiffFile]:
        """Get parsed diff for the given repository path."""
        raw = await self._git.get_raw_diff(path, base=base, ignore_whitespace=ignore_whitespace)
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
        header = self._header_lines(lines)

        path = self._extract_path(header)
        if path is None:
            return None

        status = self._detect_status(header)
        old_mode, new_mode = self._detect_mode_change(header)

        return DiffFile(
            path=path,
            status=status,
            hunks=self._parse_hunks(lines),
            is_binary=any(line.startswith("Binary files ") for line in header),
            old_mode=old_mode,
            new_mode=new_mode,
        )

    def _header_lines(self, lines: list[str]) -> list[str]:
        """Return the metadata lines that precede the first hunk.

        Hunk content carries a leading +/-/space, so a removed line reading
        "-- x" arrives as "--- x" and would otherwise look like a path marker.
        """
        for i, line in enumerate(lines):
            if line.startswith("@@"):
                return lines[:i]
        return lines

    def _extract_path(self, lines: list[str]) -> str | None:
        """Extract the file path from a file's diff chunk.

        The "a/x b/x" header holds both paths on one line with nothing but a
        space between them, so a name containing " b/" splits it wrongly. The
        markers carry exactly one path each and are preferred, in the order
        they answer "where is this file now":

        1. "+++" names the file after the change. A rename emits "--- a/old"
           and "+++ b/new", so the "+++" pass has to finish before the "---"
           one starts, or the file is reported under a path git already moved.
        2. "---" covers a deletion, where "+++" is /dev/null.
        3. "rename to" covers a rename that changed no content, which emits
           no markers at all.
        """
        for line in lines:
            if line.startswith("+++ ") and not line.startswith("+++ /dev/null"):
                return self._strip_prefix(self._read_marker_path(line[4:]))

        for line in lines:
            if line.startswith("--- ") and not line.startswith("--- /dev/null"):
                return self._strip_prefix(self._read_marker_path(line[4:]))

        for line in lines:
            if line.startswith("rename to "):
                return self._read_marker_path(line.removeprefix("rename to "))
            if line.startswith("copy to "):
                return self._read_marker_path(line.removeprefix("copy to "))

        return self._extract_header_path(lines[0])

    def _read_marker_path(self, value: str) -> str:
        """Read one path from a "---"/"+++" marker.

        Git appends a tab when the path would otherwise be ambiguous, and
        quotes the whole path when it holds characters that need escaping.
        """
        return self._unquote(value.split("\t")[0])

    def _strip_prefix(self, path: str) -> str:
        """Drop the "a/" or "b/" side prefix git puts on diff paths."""
        if path.startswith(("a/", "b/")):
            return path[2:]
        return path

    def _extract_header_path(self, header_line: str) -> str | None:
        """Extract the path from the "a/x b/x" header line.

        Only chunks with no markers and no rename reach here — binary files
        and permission changes — and for those the two halves name the same
        file. So the split is the one that makes them equal, which a name
        containing " b/" no longer defeats.
        """
        quoted = re.match(r'("(?:[^"\\]|\\.)*") ("(?:[^"\\]|\\.)*")$', header_line)
        if quoted:
            return self._strip_prefix(self._unquote(quoted.group(2)))

        if header_line.startswith("a/"):
            for i in range(2, len(header_line)):
                if header_line.startswith(" b/", i) and header_line[2:i] == header_line[i + 3 :]:
                    return header_line[2:i]

        match = re.match(r"a/(.+?) b/(.+)", header_line)
        if match:
            return match.group(2)
        return None

    def _unquote(self, value: str) -> str:
        """Decode git's C-style path quoting: '"\\320\\266.py"' -> 'ж.py'.

        Git quotes a path when it contains characters it must escape, writing
        every byte outside plain ASCII as an octal escape. Decoding collects
        the raw bytes first, because one character can span several escapes.
        """
        if not (value.startswith('"') and value.endswith('"') and len(value) >= 2):
            return value

        body = value[1:-1]
        out = bytearray()
        i = 0
        while i < len(body):
            if body[i] != "\\" or i + 1 >= len(body):
                out.extend(body[i].encode())
                i += 1
                continue

            escape = body[i + 1]
            if escape in _CONTROL_ESCAPES:
                out.append(_CONTROL_ESCAPES[escape])
                i += 2
            elif escape.isdigit():
                out.append(int(body[i + 1 : i + 4], 8))
                i += 4
            else:
                out.extend(escape.encode())
                i += 2

        return out.decode("utf-8", errors="replace")

    def _detect_status(self, lines: list[str]) -> FileStatus:
        """Detect file status from diff metadata lines."""
        for line in lines:
            if line.startswith("new file"):
                return FileStatus.ADDED
            if line.startswith("deleted file"):
                return FileStatus.DELETED
            if line.startswith("rename from"):
                return FileStatus.RENAMED
            # A copy leaves the original in place, so what is new here is a file
            if line.startswith("copy from"):
                return FileStatus.ADDED
        return FileStatus.MODIFIED

    def _detect_mode_change(self, header: list[str]) -> tuple[str | None, str | None]:
        """Read a permission change, which git reports as "old mode"/"new mode".

        A newly added file has "new file mode" instead, which is the file's
        only mode rather than a change, so it is deliberately not matched.
        """
        old_mode = new_mode = None
        for line in header:
            if line.startswith("old mode "):
                old_mode = line.removeprefix("old mode ").strip()
            elif line.startswith("new mode "):
                new_mode = line.removeprefix("new mode ").strip()
        return old_mode, new_mode

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

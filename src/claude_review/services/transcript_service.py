"""Service for reading conversation transcripts into reviewable DiffFile structures.

Reads Claude Code JSONL conversation files directly.  Consecutive messages
from the same role are merged into a single turn.  Tool calls/results,
thinking blocks, and system/command messages are excluded.
"""

import json
import re
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, LineType

# Claude Code injects internal messages (slash commands, system reminders, bash output)
# as user entries with XML tags.  These aren't real user input — filter them out.
_SYSTEM_TAG_RE = re.compile(r"^<(command-|local-command-|system-reminder|bash-)")


class Turn(BaseModel):
    """A single conversation turn after merging consecutive entries."""

    role: str
    text: str
    timestamp: str


class TranscriptService:
    """Converts a Claude Code JSONL conversation file into DiffFile models for review."""

    def parse(self, path: Path) -> list[DiffFile]:
        """Parse a Claude Code JSONL conversation file into reviewable DiffFiles.

        Each line in the JSONL is a JSON object with a ``type`` field.
        Only ``user`` and ``assistant`` entries are extracted::

            {"type": "user", "message": {"role": "user", "content": "hello"}, "timestamp": "..."}
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]},
                "timestamp": "...",
            }

        User messages have string content.  Assistant messages have a list
        of content blocks — only ``text`` blocks are extracted, ``thinking``
        and ``tool_use`` blocks are skipped.  Entries with ``type`` other
        than ``user``/``assistant`` (e.g. ``permission-mode``, ``attachment``)
        are ignored entirely.

        Consecutive same-role text entries are merged into a single turn.
        Tool calls act as turn boundaries.  Returns newest turns first.

        Raises:
            ValueError: If the file cannot be parsed.
        """
        entries = self._read_jsonl(path)
        turns = self._merge_turns(entries)

        result: list[DiffFile] = []
        for i, turn in enumerate(reversed(turns), start=1):
            lines = self._split_lines(turn.text)
            label = self._format_label(turn.role, i, turn.timestamp)
            result.append(self._build_diff_file(label, lines))

        return result

    def _read_jsonl(self, path: Path) -> list[dict]:
        """Read JSONL file, one JSON object per line."""
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            msg = f"Invalid transcript file: {e}"
            raise ValueError(msg) from e

        entries = []
        for i, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                msg = f"Invalid JSON on line {i}: {e}"
                raise ValueError(msg) from e
        return entries

    def _merge_turns(self, entries: list[dict]) -> list[Turn]:
        """Merge consecutive same-role text entries into turns.

        Tool calls and results act as turn boundaries — text before
        and after a tool call become separate turns even if the role
        is the same.
        """
        turns: list[Turn] = []
        last_had_tools = False

        for entry in entries:
            entry_type = entry.get("type")
            if entry_type not in ("user", "assistant"):
                continue

            has_tools = self._has_tool_blocks(entry)
            text = self._extract_text(entry)

            if has_tools:
                last_had_tools = True
                if not text:
                    continue
                turns.append(Turn(role=entry_type, text=text, timestamp=entry.get("timestamp", "")))
                continue

            if not text:
                continue

            timestamp = entry.get("timestamp", "")

            if turns and turns[-1].role == entry_type and not last_had_tools:
                turns[-1] = Turn(role=entry_type, text=turns[-1].text + "\n" + text, timestamp=turns[-1].timestamp)
            else:
                turns.append(Turn(role=entry_type, text=text, timestamp=timestamp))

            last_had_tools = False

        return turns

    def _has_tool_blocks(self, entry: dict) -> bool:
        """Check if an entry contains tool_use or tool_result blocks."""
        content = entry.get("message", {}).get("content")
        if not isinstance(content, list):
            return False
        return any(isinstance(b, dict) and b.get("type") in ("tool_use", "tool_result") for b in content)

    def _extract_text(self, entry: dict) -> str:
        """Extract human-readable text from a JSONL entry.

        Skips tool_use, tool_result, thinking blocks, and system/command messages.
        """
        content = entry.get("message", {}).get("content")

        if isinstance(content, str):
            text = content.strip()
            if _SYSTEM_TAG_RE.match(text):
                return ""
            return text

        if not isinstance(content, list):
            return ""

        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "").strip()
                if text and not _SYSTEM_TAG_RE.match(text):
                    parts.append(text)
        return "\n".join(parts)

    def _format_label(self, role: str, index: int, timestamp: str) -> str:
        """Format sidebar label: 'user (18:05:44) #1' or 'assistant (18:06:01) #2'."""
        time_str = ""
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                local_dt = dt.astimezone()
                time_str = f" ({local_dt:%H:%M:%S})"
            except ValueError:
                pass
        # Index suffix ensures uniqueness for the store
        return f"{role}{time_str} #{index}"

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
            old_start=0,
            new_start=1,
            lines=diff_lines,
        )
        return DiffFile(path=path, status=FileStatus.ADDED, hunks=[hunk])

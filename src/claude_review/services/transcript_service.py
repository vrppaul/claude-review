"""Service for reading conversation transcripts into reviewable DiffFile structures.

Reads Claude Code JSONL conversation files directly.  Consecutive messages
from the same role are merged into a single turn.  Tool calls/results,
thinking blocks, and system/command messages are excluded.
"""

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, LineType

# Claude Code injects internal messages (slash commands, system reminders, bash output)
# as user entries with XML tags.  These aren't real user input — filter them out.
_SYSTEM_TAG_RE = re.compile(r"^<(command-|local-command-|system-reminder|bash-)")

# The entry types that are one side of the conversation
CONVERSATION_ROLES = frozenset({"user", "assistant"})
# The content blocks that call a tool or carry its result, which end a turn
TOOL_BLOCKS = frozenset({"tool_use", "tool_result"})
TEXT_BLOCK = "text"


class ContentBlock(BaseModel):
    """One block of a message: text, thinking, a tool call or its result."""

    type: str
    text: str | None = None


class EntryMessage(BaseModel):
    """What one entry says: plain text from the user, or blocks."""

    content: str | list[ContentBlock] | None = None


class TranscriptEntry(BaseModel):
    """One line of a Claude Code transcript; whatever it carries besides is ignored."""

    type: str
    message: EntryMessage | None = None
    timestamp: str = ""
    # Written in the user's name by the tool itself: a skill's instructions, a
    # pasted image's note, a subagent's report
    is_meta: bool = Field(default=False, alias="isMeta")
    # A subagent's own conversation, run beside the main one
    is_sidechain: bool = Field(default=False, alias="isSidechain")


class ConversationTurn(BaseModel):
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
        are ignored entirely, and so are entries the tool wrote in the
        user's name and a subagent's side conversation.

        Consecutive same-role text entries are merged into a single turn.
        Tool calls act as turn boundaries.  Returns newest turns first.

        Raises:
            ValueError: If the file cannot be parsed.
        """
        turns = self._merge_turns(self._read_jsonl(path))
        labels = _labels(turns)
        return [
            self._build_diff_file(label, self._split_lines(turn.text))
            for turn, label in reversed(list(zip(turns, labels, strict=True)))
        ]

    def _read_jsonl(self, path: Path) -> list[TranscriptEntry]:
        """Read the conversation's entries, one JSON object per line.

        An entry whose shape this does not know is left out rather than read
        wrongly: the transcript's format belongs to another program.
        """
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            msg = f"Invalid transcript file: {e}"
            raise ValueError(msg) from e

        entries = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as e:
                msg = f"Invalid JSON on line {line_number}: {e}"
                raise ValueError(msg) from e
            try:
                entries.append(TranscriptEntry.model_validate(raw))
            except ValidationError:
                continue
        return entries

    def _merge_turns(self, entries: list[TranscriptEntry]) -> list[ConversationTurn]:
        """Merge consecutive same-role text entries into turns.

        Tool calls and results act as turn boundaries — text before
        and after a tool call become separate turns even if the role
        is the same.
        """
        turns: list[ConversationTurn] = []
        last_had_tools = False

        for entry in entries:
            if entry.type not in CONVERSATION_ROLES or entry.is_meta or entry.is_sidechain:
                continue

            has_tools = _has_tool_blocks(entry)
            text = _extract_text(entry)

            if has_tools:
                last_had_tools = True
                if text:
                    turns.append(ConversationTurn(role=entry.type, text=text, timestamp=entry.timestamp))
                continue

            if not text:
                continue

            if turns and turns[-1].role == entry.type and not last_had_tools:
                turns[-1] = turns[-1].model_copy(update={"text": f"{turns[-1].text}\n{text}"})
            else:
                turns.append(ConversationTurn(role=entry.type, text=text, timestamp=entry.timestamp))

            last_had_tools = False

        return turns

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


def _has_tool_blocks(entry: TranscriptEntry) -> bool:
    """Whether an entry calls a tool or carries a tool's result."""
    content = entry.message.content if entry.message else None
    return isinstance(content, list) and any(block.type in TOOL_BLOCKS for block in content)


def _extract_text(entry: TranscriptEntry) -> str:
    """The human-readable text of an entry, without system and command messages."""
    content = entry.message.content if entry.message else None

    if isinstance(content, str):
        text = content.strip()
        return "" if _SYSTEM_TAG_RE.match(text) else text

    if content is None:
        return ""

    said = [(block.text or "").strip() for block in content if block.type == TEXT_BLOCK]
    return "\n".join(text for text in said if text and not _SYSTEM_TAG_RE.match(text))


def _labels(turns: list[ConversationTurn]) -> list[str]:
    """Name each turn by who spoke and when: 'user (18:05:44)'.

    The name is what threads and the unsent draft hang on, so it never
    depends on how much of the conversation came after: two turns in the
    same second are told apart by their order, counted from the start.
    """
    seen: Counter[str] = Counter()
    labels = []
    for turn in turns:
        label = f"{turn.role}{_said_at(turn.timestamp)}"
        seen[label] += 1
        labels.append(label if seen[label] == 1 else f"{label} #{seen[label]}")
    return labels


def _said_at(timestamp: str) -> str:
    """When a turn was said, in local time, or nothing when the entry does not say."""
    if not timestamp:
        return ""
    try:
        return f" ({datetime.fromisoformat(timestamp).astimezone():%H:%M:%S})"
    except ValueError:
        return ""

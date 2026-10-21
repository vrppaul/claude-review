"""A conversation, read for review from the transcript Claude Code keeps of it.

Reads Claude Code JSONL conversation files directly.  Consecutive messages
from the same role are merged into a single turn.  Tool calls/results,
thinking blocks, and system/command messages are excluded.
"""

import asyncio
import json
import re
from collections import Counter
from datetime import datetime
from enum import StrEnum, auto
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from claude_review.domain.models import FIRST_LINE, DiffFile
from claude_review.services.unreadable_content import UnreadableContentError
from claude_review.services.whole_file import whole_file

# Claude Code injects internal messages (slash commands, system reminders, bash output)
# as user entries with XML tags.  These aren't real user input — filter them out.
SYSTEM_TAG = re.compile(r"^<(command-|local-command-|system-reminder|bash-)")

# The content blocks that call a tool or carry its result, which end a turn
TOOL_BLOCKS = frozenset({"tool_use", "tool_result"})
TEXT_BLOCK = "text"

# What ends an entry of the transcript, and nothing else does. Python's own
# line splitting also breaks at U+2028, U+2029 and U+0085, which Node writes
# unescaped inside a string: one such character anywhere, in a tool's result
# even, would cut an entry in two and refuse the whole transcript.
ENTRY_END = "\n"
# What the transcript is written in
TRANSCRIPT_ENCODING = "utf-8"
# How much of an id Claude Code gives — a conversation's or one of its
# entries' — names it: its first group of hex digits, enough to tell one's
# conversations, or a conversation's turns, apart, as a short commit id
# tells commits apart
SHORT_ID_LENGTH = 8
# How a turn is named: who spoke, then the id of the entry it began with, or
# without one the local time it was said at; and how a name already taken is
# numbered again
NAMED_BY_ID = "{speaker} {entry_id}"
NAMED_BY_TIME = "{speaker} ({said_at:%H:%M:%S})"
REPEATED_NAME = "{name} #{count}"
# What parts the entries merged into one turn: each starts a line of its own
TURN_LINE_BREAK = "\n"


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
    # The entry's own id, which Claude Code gives every one it writes
    uuid: str | None = None
    # The id of the conversation it is part of, which Claude Code also names the file by
    session_id: str | None = Field(default=None, alias="sessionId")
    # Written in the user's name by the tool itself: a skill's instructions, a
    # pasted image's note, a subagent's report
    is_meta: bool = Field(default=False, alias="isMeta")
    # A subagent's own conversation, run beside the main one
    is_sidechain: bool = Field(default=False, alias="isSidechain")


class Speaker(StrEnum):
    """The side of the conversation an entry is from: the entry types that are one."""

    USER = auto()
    ASSISTANT = auto()


class ConversationTurn(BaseModel):
    """A single conversation turn after merging consecutive entries."""

    speaker: Speaker
    text: str
    timestamp: str
    # The id of the entry it began with, when the transcript gives one
    entry_id: str | None


class Transcript(BaseModel):
    """A conversation as read for review: the session it is, and its turns."""

    model_config = ConfigDict(frozen=True)

    # The id Claude Code gives the conversation
    session_id: str
    # Each turn a reviewable file, newest first
    turns: list[DiffFile]


async def read_transcript(path: Path) -> Transcript:
    """A Claude Code JSONL conversation, the session it is and each turn a reviewable file; read on a thread.

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
    Tool calls act as turn boundaries.

    Raises:
        UnreadableContentError: If the file cannot be read, a line is not
            JSON, or no entry names the session.
    """
    return await asyncio.to_thread(_transcript_of, path)


def _transcript_of(path: Path) -> Transcript:
    """The conversation's session and its turns as files, newest first: the file read and parsed in one go."""
    entries = _entries(_read_text(path))
    turns = _merge_turns(entries)
    labels = _labels(turns)
    return Transcript(
        session_id=_session_of(entries),
        turns=[whole_file(label, turn.text) for turn, label in reversed(list(zip(turns, labels, strict=True)))],
    )


def _session_of(entries: list[TranscriptEntry]) -> str:
    """The session the conversation is, which Claude Code names on every entry but its records of a file's history.

    Raises:
        UnreadableContentError: If no entry names it, so the file is no conversation Claude Code kept.
    """
    session_id = next((entry.session_id for entry in entries if entry.session_id is not None), None)
    if session_id is None:
        msg = "No entry names the session: not a conversation Claude Code kept"
        raise UnreadableContentError(msg)
    return session_id


def _read_text(path: Path) -> str:
    """The conversation file's text.

    Raises:
        UnreadableContentError: If the file cannot be read, or is not UTF-8.
    """
    try:
        return path.read_text(encoding=TRANSCRIPT_ENCODING)
    except (OSError, UnicodeDecodeError) as error:
        msg = f"Invalid transcript file: {error}"
        raise UnreadableContentError(msg) from error


def _entries(text: str) -> list[TranscriptEntry]:
    """The conversation's entries, one JSON object per line.

    A line that is not JSON makes the file unreadable; an entry whose shape
    this does not know is left out rather than read wrongly, since the
    transcript's format belongs to another program. The two are told apart
    by reading each line in two steps.

    Raises:
        UnreadableContentError: If a line is not JSON.
    """
    entries = []
    for line_number, line in enumerate(text.split(ENTRY_END), start=FIRST_LINE):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            msg = f"Invalid JSON on line {line_number}: {error}"
            raise UnreadableContentError(msg) from error
        try:
            entries.append(TranscriptEntry.model_validate(raw))
        except ValidationError:
            continue
    return entries


def _merge_turns(entries: list[TranscriptEntry]) -> list[ConversationTurn]:
    """Merge consecutive same-speaker text entries into turns.

    Tool calls and results act as turn boundaries — text before
    and after a tool call become separate turns even if the speaker
    is the same.
    """
    turns: list[ConversationTurn] = []
    last_had_tools = False

    for entry in entries:
        if entry.type not in Speaker or entry.is_meta or entry.is_sidechain:
            continue

        speaker = Speaker(entry.type)
        has_tools = _has_tool_blocks(entry)
        text = _extract_text(entry)

        if has_tools:
            last_had_tools = True
            if text:
                turns.append(_turn(speaker, text, entry))
            continue

        if not text:
            continue

        if turns and turns[-1].speaker == speaker and not last_had_tools:
            turns[-1] = _continued(turns[-1], text)
        else:
            turns.append(_turn(speaker, text, entry))

        last_had_tools = False

    return turns


def _turn(speaker: Speaker, text: str, entry: TranscriptEntry) -> ConversationTurn:
    """A turn that begins with this entry."""
    return ConversationTurn(speaker=speaker, text=text, timestamp=entry.timestamp, entry_id=entry.uuid)


def _continued(turn: ConversationTurn, text: str) -> ConversationTurn:
    """A turn with more said in it by the same speaker."""
    return ConversationTurn(
        speaker=turn.speaker,
        text=TURN_LINE_BREAK.join((turn.text, text)),
        timestamp=turn.timestamp,
        entry_id=turn.entry_id,
    )


def _has_tool_blocks(entry: TranscriptEntry) -> bool:
    """Whether an entry calls a tool or carries a tool's result."""
    content = entry.message.content if entry.message else None
    return isinstance(content, list) and any(block.type in TOOL_BLOCKS for block in content)


def _extract_text(entry: TranscriptEntry) -> str:
    """The human-readable text of an entry, without system and command messages."""
    content = entry.message.content if entry.message else None

    if isinstance(content, str):
        text = content.strip()
        return "" if SYSTEM_TAG.match(text) else text

    if content is None:
        return ""

    said = [(block.text or "").strip() for block in content if block.type == TEXT_BLOCK]
    return "\n".join(text for text in said if text and not SYSTEM_TAG.match(text))


def _labels(turns: list[ConversationTurn]) -> list[str]:
    """Name each turn by who spoke and the id of the entry it began with: 'user f260656f'.

    The name is what threads and the unsent draft hang on, so it depends
    neither on how much of the conversation came after nor on the time zone
    the transcript is read in. A turn whose entry has no id is named by when
    it was said, in local time: 'user (18:05:44)'. Two turns that would
    share a name are told apart by their order, counted from the start.
    """
    seen: Counter[str] = Counter()
    labels = []
    for turn in turns:
        name = _name_of(turn)
        seen[name] += 1
        labels.append(name if seen[name] == 1 else REPEATED_NAME.format(name=name, count=seen[name]))
    return labels


def _name_of(turn: ConversationTurn) -> str:
    """Who spoke, and what tells the turn apart: the id of the entry it began with, or when it was said."""
    if turn.entry_id:
        return NAMED_BY_ID.format(speaker=turn.speaker, entry_id=turn.entry_id[:SHORT_ID_LENGTH])
    said_at = _said_at(turn.timestamp)
    return NAMED_BY_TIME.format(speaker=turn.speaker, said_at=said_at) if said_at else str(turn.speaker)


def _said_at(timestamp: str) -> datetime | None:
    """When a turn was said, in local time, or None when the entry does not say."""
    if not timestamp:
        return None
    try:
        return datetime.fromisoformat(timestamp).astimezone()
    except ValueError:
        return None

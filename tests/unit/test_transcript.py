"""Functional tests for reading a conversation for review.

These test user-facing behavior: can a Claude Code JSONL conversation
be loaded and reviewed — not the internal data structures used to represent it.
"""

import json
from pathlib import Path

import pytest

from claude_review.domain.models import DiffFile
from claude_review.services.transcript import read_transcript
from claude_review.services.unreadable_content import UnreadableContentError


def _write_jsonl(path: Path, entries: list[dict]) -> Path:
    """Write entries as JSONL (one JSON object per line)."""
    conversation = path / "conversation.jsonl"
    conversation.write_text("\n".join(json.dumps(entry) for entry in entries))
    return conversation


def _user(content: str, timestamp: str = "") -> dict:
    return {"type": "user", "message": {"role": "user", "content": content}, "timestamp": timestamp}


def _user_blocks(blocks: list[dict]) -> dict:
    return {"type": "user", "message": {"role": "user", "content": blocks}, "timestamp": ""}


def _assistant(text: str, timestamp: str = "") -> dict:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
        "timestamp": timestamp,
    }


def _assistant_thinking(thinking: str) -> dict:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "thinking", "thinking": thinking}]},
        "timestamp": "",
    }


def _assistant_tool_use(name: str) -> dict:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "tool_use", "name": name, "input": {}}]},
        "timestamp": "",
    }


def _turn_texts(turns: list[DiffFile]) -> list[list[str]]:
    """Every line of every turn, newest turn first."""
    return [[line.content for hunk in turn.hunks for line in hunk.lines] for turn in turns]


def _first_lines(turns: list[DiffFile]) -> list[str]:
    """What each turn says first, newest turn first."""
    return [turn.hunks[0].lines[0].content for turn in turns]


def _names_by_first_line(turns: list[DiffFile]) -> dict[str, str]:
    """The name each turn is reviewed under, found by the first line it says."""
    return {turn.hunks[0].lines[0].content: turn.path for turn in turns}


def _user_tool_result() -> dict:
    return _user_blocks([{"type": "tool_result", "content": "ok"}])


class TestRead:
    async def test_single_message(self, tmp_path: Path) -> None:
        conversation = _write_jsonl(tmp_path, [_user("hello world")])
        result = await read_transcript(conversation)

        assert len(result) == 1
        assert "user" in result[0].path

    async def test_newest_messages_first(self, tmp_path: Path) -> None:
        """Messages are reversed — newest turn appears first in sidebar."""
        conversation = _write_jsonl(
            tmp_path,
            [
                _user("first question"),
                _assistant("first answer"),
                _user("second question"),
            ],
        )

        result = await read_transcript(conversation)

        assert _first_lines(result) == ["second question", "first answer", "first question"]

    async def test_consecutive_same_role_merged(self, tmp_path: Path) -> None:
        """Consecutive text entries from same role merge into one turn."""
        conversation = _write_jsonl(
            tmp_path,
            [
                _user("do something"),
                _assistant("Here is part one"),
                _assistant("Here is part two"),
            ],
        )

        result = await read_transcript(conversation)

        assert _first_lines(result) == ["Here is part one", "do something"]
        content = "\n".join(line.content for line in result[0].hunks[0].lines)
        assert "part one" in content
        assert "part two" in content

    async def test_thinking_and_tool_use_excluded(self, tmp_path: Path) -> None:
        conversation = _write_jsonl(
            tmp_path,
            [
                _user("question"),
                _assistant_thinking("let me think..."),
                _assistant("Here is my answer"),
                _assistant_tool_use("Read"),
            ],
        )

        result = await read_transcript(conversation)
        assert _first_lines(result) == ["Here is my answer", "question"]
        content = "\n".join(line.content for line in result[0].hunks[0].lines)
        assert "my answer" in content
        assert "think" not in content

    async def test_tool_calls_break_turns(self, tmp_path: Path) -> None:
        """Text separated by tool calls becomes separate turns."""
        conversation = _write_jsonl(
            tmp_path,
            [
                _user("question"),
                _assistant("let me check"),
                _assistant_tool_use("Bash"),
                _user_tool_result(),
                _assistant("the answer is 42"),
            ],
        )

        result = await read_transcript(conversation)

        assert _first_lines(result) == ["the answer is 42", "let me check", "question"]

    async def test_system_command_messages_excluded(self, tmp_path: Path) -> None:
        conversation = _write_jsonl(
            tmp_path,
            [
                _user("real question"),
                _user("<command-name>/review-ui</command-name>"),
                _user("<local-command-caveat>Caveat: ...</local-command-caveat>\nstuff"),
                _assistant("real answer"),
            ],
        )

        result = await read_transcript(conversation)

        assert _first_lines(result) == ["real answer", "real question"]
        user_content = "\n".join(line.content for line in result[1].hunks[0].lines)
        assert "real question" in user_content
        assert "command" not in user_content

    async def test_non_message_entries_skipped(self, tmp_path: Path) -> None:
        conversation = _write_jsonl(
            tmp_path,
            [
                {"type": "permission-mode", "permissionMode": "default"},
                _user("hello"),
                {"type": "attachment", "data": {}},
                _assistant("world"),
            ],
        )

        result = await read_transcript(conversation)
        assert _first_lines(result) == ["world", "hello"]

    async def test_content_preserved_line_by_line(self, tmp_path: Path) -> None:
        conversation = _write_jsonl(tmp_path, [_user("line one\nline two\nline three")])

        result = await read_transcript(conversation)
        content = [line.content for line in result[0].hunks[0].lines]

        assert content == ["line one", "line two", "line three"]

    async def test_every_line_has_commentable_line_number(self, tmp_path: Path) -> None:
        conversation = _write_jsonl(tmp_path, [_assistant("first\nsecond\nthird")])

        result = await read_transcript(conversation)
        numbers = [line.new_number for line in result[0].hunks[0].lines]

        assert numbers == [1, 2, 3]

    async def test_empty_messages_skipped(self, tmp_path: Path) -> None:
        conversation = _write_jsonl(
            tmp_path,
            [
                _user(""),
                _assistant("real content"),
            ],
        )

        result = await read_transcript(conversation)
        assert len(result) == 1

    async def test_timestamp_in_label(self, tmp_path: Path) -> None:
        conversation = _write_jsonl(tmp_path, [_user("hello", timestamp="2026-04-04T18:05:44.342Z")])

        result = await read_transcript(conversation)
        assert "user" in result[0].path
        assert ")" in result[0].path

    async def test_labels_are_unique(self, tmp_path: Path) -> None:
        """Each turn gets a unique path so the store can select by path."""
        conversation = _write_jsonl(
            tmp_path,
            [
                _user("a", timestamp="2026-04-04T18:05:00.000Z"),
                _assistant("b", timestamp="2026-04-04T18:05:00.000Z"),
                _user("c", timestamp="2026-04-04T18:05:00.000Z"),
            ],
        )

        result = await read_transcript(conversation)
        paths = [turn.path for turn in result]

        assert len(paths) == len(set(paths))

    async def test_no_visible_messages_produces_empty_result(self, tmp_path: Path) -> None:
        """JSONL with only non-message entries produces no turns."""
        conversation = _write_jsonl(
            tmp_path,
            [
                {"type": "permission-mode", "permissionMode": "default"},
                {"type": "attachment", "data": {}},
            ],
        )

        result = await read_transcript(conversation)

        assert len(result) == 0

    async def test_malformed_content_skipped(self, tmp_path: Path) -> None:
        """Entries with null or non-standard content are skipped, not crashed on."""
        conversation = _write_jsonl(
            tmp_path,
            [
                {"type": "user", "message": {"role": "user", "content": None}, "timestamp": ""},
                _assistant("real answer"),
            ],
        )

        result = await read_transcript(conversation)

        assert len(result) == 1
        assert result[0].hunks[0].lines[0].content == "real answer"

    async def test_invalid_jsonl_raises_error(self, tmp_path: Path) -> None:
        conversation = tmp_path / "conversation.jsonl"
        conversation.write_text("not json\n")

        with pytest.raises(UnreadableContentError, match="Invalid JSON"):
            await read_transcript(conversation)


class TestWhatIsATurn:
    async def test_text_the_tool_put_in_the_users_name_is_not_a_turn(self, tmp_path: Path) -> None:
        """A skill's instructions, a pasted image's note, a subagent's report:
        written for the model, not by the user."""
        injected = {**_user("Base directory for this skill: /skills/review"), "isMeta": True}
        transcript = _write_jsonl(tmp_path, [_user("Review this"), injected])

        assert _turn_texts(await read_transcript(transcript)) == [["Review this"]]

    async def test_a_side_conversation_is_not_part_of_the_transcript(self, tmp_path: Path) -> None:
        side = {**_assistant("subagent musing"), "isSidechain": True}
        transcript = _write_jsonl(tmp_path, [_user("Review this"), side])

        assert _turn_texts(await read_transcript(transcript)) == [["Review this"]]


class TestLabels:
    async def test_a_turn_keeps_its_name_as_the_conversation_grows(self, tmp_path: Path) -> None:
        """Threads and the unsent draft hang on these names; a live session keeps growing."""
        earlier = [
            _user("first", timestamp="2026-04-04T18:05:00.000Z"),
            _assistant("answer", timestamp="2026-04-04T18:05:00.000Z"),
        ]
        before = _names_by_first_line(await read_transcript(_write_jsonl(tmp_path, earlier)))

        grown = [*earlier, _user("second", timestamp="2026-04-04T18:06:00.000Z")]
        after = _names_by_first_line(await read_transcript(_write_jsonl(tmp_path, grown)))

        assert after["first"] == before["first"]
        assert after["answer"] == before["answer"]

    async def test_two_turns_in_the_same_second_are_told_apart(self, tmp_path: Path) -> None:
        same_second = "2026-04-04T18:05:00.000Z"
        transcript = _write_jsonl(
            tmp_path,
            [
                _user("a", timestamp=same_second),
                _assistant("b", timestamp=same_second),
                _user("c", timestamp=same_second),
            ],
        )

        paths = [turn.path for turn in await read_transcript(transcript)]

        assert len(set(paths)) == len(paths)

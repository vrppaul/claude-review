"""Functional tests for TranscriptService.

These test user-facing behavior: can a Claude Code JSONL conversation
be loaded and reviewed — not the internal data structures used to represent it.
"""

import json
from pathlib import Path

import pytest

from claude_review.domain.exceptions import UnreadableContentError
from claude_review.domain.models import DiffFile
from claude_review.services.transcript_service import TranscriptService


@pytest.fixture
def service() -> TranscriptService:
    return TranscriptService()


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


def _user_tool_result() -> dict:
    return _user_blocks([{"type": "tool_result", "content": "ok"}])


class TestParse:
    def test_single_message(self, service: TranscriptService, tmp_path: Path) -> None:
        conversation = _write_jsonl(tmp_path, [_user("hello world")])
        result = service.parse(conversation)

        assert len(result) == 1
        assert "user" in result[0].path

    def test_newest_messages_first(self, service: TranscriptService, tmp_path: Path) -> None:
        """Messages are reversed — newest turn appears first in sidebar."""
        conversation = _write_jsonl(
            tmp_path,
            [
                _user("first question"),
                _assistant("first answer"),
                _user("second question"),
            ],
        )

        result = service.parse(conversation)
        contents = [message.hunks[0].lines[0].content for message in result]

        assert contents == ["second question", "first answer", "first question"]

    def test_consecutive_same_role_merged(self, service: TranscriptService, tmp_path: Path) -> None:
        """Consecutive text entries from same role merge into one turn."""
        conversation = _write_jsonl(
            tmp_path,
            [
                _user("do something"),
                _assistant("Here is part one"),
                _assistant("Here is part two"),
            ],
        )

        result = service.parse(conversation)

        assert len(result) == 2
        content = "\n".join(line.content for line in result[0].hunks[0].lines)
        assert "part one" in content
        assert "part two" in content

    def test_thinking_and_tool_use_excluded(self, service: TranscriptService, tmp_path: Path) -> None:
        conversation = _write_jsonl(
            tmp_path,
            [
                _user("question"),
                _assistant_thinking("let me think..."),
                _assistant("Here is my answer"),
                _assistant_tool_use("Read"),
            ],
        )

        result = service.parse(conversation)
        assert len(result) == 2
        content = "\n".join(line.content for line in result[0].hunks[0].lines)
        assert "my answer" in content
        assert "think" not in content

    def test_tool_calls_break_turns(self, service: TranscriptService, tmp_path: Path) -> None:
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

        result = service.parse(conversation)

        assert len(result) == 3
        # Newest first
        assert result[0].hunks[0].lines[0].content == "the answer is 42"
        assert result[1].hunks[0].lines[0].content == "let me check"
        assert result[2].hunks[0].lines[0].content == "question"

    def test_system_command_messages_excluded(self, service: TranscriptService, tmp_path: Path) -> None:
        conversation = _write_jsonl(
            tmp_path,
            [
                _user("real question"),
                _user("<command-name>/review-ui</command-name>"),
                _user("<local-command-caveat>Caveat: ...</local-command-caveat>\nstuff"),
                _assistant("real answer"),
            ],
        )

        result = service.parse(conversation)

        assert len(result) == 2
        user_content = "\n".join(line.content for line in result[1].hunks[0].lines)
        assert "real question" in user_content
        assert "command" not in user_content

    def test_non_message_entries_skipped(self, service: TranscriptService, tmp_path: Path) -> None:
        conversation = _write_jsonl(
            tmp_path,
            [
                {"type": "permission-mode", "permissionMode": "default"},
                _user("hello"),
                {"type": "attachment", "data": {}},
                _assistant("world"),
            ],
        )

        result = service.parse(conversation)
        assert len(result) == 2

    def test_content_preserved_line_by_line(self, service: TranscriptService, tmp_path: Path) -> None:
        conversation = _write_jsonl(tmp_path, [_user("line one\nline two\nline three")])

        result = service.parse(conversation)
        content = [line.content for line in result[0].hunks[0].lines]

        assert content == ["line one", "line two", "line three"]

    def test_every_line_has_commentable_line_number(self, service: TranscriptService, tmp_path: Path) -> None:
        conversation = _write_jsonl(tmp_path, [_assistant("first\nsecond\nthird")])

        result = service.parse(conversation)
        numbers = [line.new_no for line in result[0].hunks[0].lines]

        assert numbers == [1, 2, 3]

    def test_empty_messages_skipped(self, service: TranscriptService, tmp_path: Path) -> None:
        conversation = _write_jsonl(
            tmp_path,
            [
                _user(""),
                _assistant("real content"),
            ],
        )

        result = service.parse(conversation)
        assert len(result) == 1

    def test_timestamp_in_label(self, service: TranscriptService, tmp_path: Path) -> None:
        conversation = _write_jsonl(tmp_path, [_user("hello", timestamp="2026-04-04T18:05:44.342Z")])

        result = service.parse(conversation)
        assert "user" in result[0].path
        assert ")" in result[0].path

    def test_labels_are_unique(self, service: TranscriptService, tmp_path: Path) -> None:
        """Each turn gets a unique path so the store can select by path."""
        conversation = _write_jsonl(
            tmp_path,
            [
                _user("a", timestamp="2026-04-04T18:05:00.000Z"),
                _assistant("b", timestamp="2026-04-04T18:05:00.000Z"),
                _user("c", timestamp="2026-04-04T18:05:00.000Z"),
            ],
        )

        result = service.parse(conversation)
        paths = [r.path for r in result]

        assert len(paths) == len(set(paths))

    def test_no_visible_messages_produces_empty_result(self, service: TranscriptService, tmp_path: Path) -> None:
        """JSONL with only non-message entries produces no turns."""
        conversation = _write_jsonl(
            tmp_path,
            [
                {"type": "permission-mode", "permissionMode": "default"},
                {"type": "attachment", "data": {}},
            ],
        )

        result = service.parse(conversation)

        assert len(result) == 0

    def test_malformed_content_skipped(self, service: TranscriptService, tmp_path: Path) -> None:
        """Entries with null or non-standard content are skipped, not crashed on."""
        conversation = _write_jsonl(
            tmp_path,
            [
                {"type": "user", "message": {"role": "user", "content": None}, "timestamp": ""},
                _assistant("real answer"),
            ],
        )

        result = service.parse(conversation)

        assert len(result) == 1
        assert result[0].hunks[0].lines[0].content == "real answer"

    def test_invalid_jsonl_raises_error(self, service: TranscriptService, tmp_path: Path) -> None:
        conversation = tmp_path / "conversation.jsonl"
        conversation.write_text("not json\n")

        with pytest.raises(UnreadableContentError, match="Invalid JSON"):
            service.parse(conversation)


class TestWhatIsATurn:
    def test_text_the_tool_put_in_the_users_name_is_not_a_turn(
        self, service: TranscriptService, tmp_path: Path
    ) -> None:
        """A skill's instructions, a pasted image's note, a subagent's report:
        written for the model, not by the user."""
        injected = {**_user("Base directory for this skill: /skills/review"), "isMeta": True}
        transcript = _write_jsonl(tmp_path, [_user("Review this"), injected])

        assert _turn_texts(service.parse(transcript)) == [["Review this"]]

    def test_a_side_conversation_is_not_part_of_the_transcript(
        self, service: TranscriptService, tmp_path: Path
    ) -> None:
        side = {**_assistant("subagent musing"), "isSidechain": True}
        transcript = _write_jsonl(tmp_path, [_user("Review this"), side])

        assert _turn_texts(service.parse(transcript)) == [["Review this"]]


class TestLabels:
    def test_a_turn_keeps_its_name_as_the_conversation_grows(self, service: TranscriptService, tmp_path: Path) -> None:
        """Threads and the unsent draft hang on these names; a live session keeps growing."""
        earlier = [
            _user("first", timestamp="2026-04-04T18:05:00.000Z"),
            _assistant("answer", timestamp="2026-04-04T18:05:00.000Z"),
        ]
        before = {r.hunks[0].lines[0].content: r.path for r in service.parse(_write_jsonl(tmp_path, earlier))}

        grown = [*earlier, _user("second", timestamp="2026-04-04T18:06:00.000Z")]
        after = {r.hunks[0].lines[0].content: r.path for r in service.parse(_write_jsonl(tmp_path, grown))}

        assert after["first"] == before["first"]
        assert after["answer"] == before["answer"]

    def test_two_turns_in_the_same_second_are_told_apart(self, service: TranscriptService, tmp_path: Path) -> None:
        same_second = "2026-04-04T18:05:00.000Z"
        transcript = _write_jsonl(
            tmp_path,
            [
                _user("a", timestamp=same_second),
                _assistant("b", timestamp=same_second),
                _user("c", timestamp=same_second),
            ],
        )

        paths = [r.path for r in service.parse(transcript)]

        assert len(set(paths)) == 3

"""Functional tests for reading a conversation for review.

These test user-facing behavior: can a Claude Code JSONL conversation
be loaded and reviewed — not the internal data structures used to represent it.
"""

import json
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from claude_review.domain.models import DiffFile
from claude_review.services.transcript import read_transcript
from claude_review.services.unreadable_content import UnreadableContentError
from tests.helpers import SESSION_ID


def _write_jsonl(path: Path, entries: list[dict]) -> Path:
    """Write entries as JSONL (one JSON object per line)."""
    conversation = path / "conversation.jsonl"
    conversation.write_text("\n".join(json.dumps(entry) for entry in entries))
    return conversation


async def _turns_of(conversation: Path) -> list[DiffFile]:
    """The conversation's turns as they are read for review, newest first."""
    return (await read_transcript(conversation)).turns


def _user(content: str, timestamp: str = "") -> dict:
    return {
        "type": "user",
        "sessionId": SESSION_ID,
        "message": {"role": "user", "content": content},
        "timestamp": timestamp,
    }


def _user_blocks(blocks: list[dict]) -> dict:
    return {"type": "user", "sessionId": SESSION_ID, "message": {"role": "user", "content": blocks}, "timestamp": ""}


def _assistant(text: str, timestamp: str = "") -> dict:
    return {
        "type": "assistant",
        "sessionId": SESSION_ID,
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
        "timestamp": timestamp,
    }


def _assistant_thinking(thinking: str) -> dict:
    return {
        "type": "assistant",
        "sessionId": SESSION_ID,
        "message": {"role": "assistant", "content": [{"type": "thinking", "thinking": thinking}]},
        "timestamp": "",
    }


def _assistant_tool_use(name: str) -> dict:
    return {
        "type": "assistant",
        "sessionId": SESSION_ID,
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

        result = await _turns_of(conversation)

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

        result = await _turns_of(conversation)

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

        result = await _turns_of(conversation)
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

        result = await _turns_of(conversation)

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

        result = await _turns_of(conversation)

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

        result = await _turns_of(conversation)
        assert _first_lines(result) == ["world", "hello"]

    async def test_content_preserved_line_by_line(self, tmp_path: Path) -> None:
        conversation = _write_jsonl(tmp_path, [_user("line one\nline two\nline three")])

        result = await _turns_of(conversation)
        content = [line.content for line in result[0].hunks[0].lines]

        assert content == ["line one", "line two", "line three"]

    async def test_empty_messages_skipped(self, tmp_path: Path) -> None:
        conversation = _write_jsonl(
            tmp_path,
            [
                _user(""),
                _assistant("real content"),
            ],
        )

        result = await _turns_of(conversation)
        assert len(result) == 1

    async def test_no_visible_messages_produces_empty_result(self, tmp_path: Path) -> None:
        """JSONL with only non-message entries produces no turns."""
        conversation = _write_jsonl(
            tmp_path,
            [
                {"type": "permission-mode", "sessionId": SESSION_ID, "permissionMode": "default"},
                {"type": "attachment", "sessionId": SESSION_ID, "data": {}},
            ],
        )

        result = await _turns_of(conversation)

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

        result = await _turns_of(conversation)

        assert len(result) == 1
        assert result[0].hunks[0].lines[0].content == "real answer"

    async def test_invalid_jsonl_raises_error(self, tmp_path: Path) -> None:
        conversation = tmp_path / "conversation.jsonl"
        conversation.write_text("not json\n")

        with pytest.raises(UnreadableContentError, match="Invalid JSON"):
            await _turns_of(conversation)

    @pytest.mark.parametrize(
        "entries", [[], [{"type": "user", "message": {"role": "user", "content": "hello"}}]], ids=["empty", "unnamed"]
    )
    async def test_a_transcript_no_entry_of_which_names_its_session_is_refused(
        self, tmp_path: Path, entries: list[dict]
    ) -> None:
        """Claude Code names the session on every entry it writes: without one, this is not its conversation."""
        with pytest.raises(UnreadableContentError, match="No entry names the session"):
            await _turns_of(_write_jsonl(tmp_path, entries))

    @pytest.mark.parametrize(
        "separator", ["\u2028", "\u2029", "\u0085"], ids=["line-separator", "paragraph-separator", "next-line"]
    )
    async def test_a_line_break_of_unicode_inside_a_message_leaves_it_one_line(
        self, tmp_path: Path, separator: str
    ) -> None:
        """Node writes these unescaped inside a string; only "\\n" ends a line of JSONL."""
        conversation = tmp_path / "conversation.jsonl"
        said = f"before{separator}after"
        conversation.write_text(json.dumps(_user(said), ensure_ascii=False) + "\n", encoding="utf-8")

        [turn] = await _turns_of(conversation)

        assert [line.content for line in turn.hunks[0].lines] == [said]


class TestWhatIsATurn:
    async def test_text_the_tool_put_in_the_users_name_is_not_a_turn(self, tmp_path: Path) -> None:
        """A skill's instructions, a pasted image's note, a subagent's report:
        written for the model, not by the user."""
        injected = {**_user("Base directory for this skill: /skills/review"), "isMeta": True}
        transcript = _write_jsonl(tmp_path, [_user("Review this"), injected])

        assert _turn_texts(await _turns_of(transcript)) == [["Review this"]]

    async def test_a_side_conversation_is_not_part_of_the_transcript(self, tmp_path: Path) -> None:
        side = {**_assistant("subagent musing"), "isSidechain": True}
        transcript = _write_jsonl(tmp_path, [_user("Review this"), side])

        assert _turn_texts(await _turns_of(transcript)) == [["Review this"]]


class TestLabels:
    async def test_a_turn_keeps_its_name_as_the_conversation_grows(self, tmp_path: Path) -> None:
        """Threads and the unsent draft hang on these names; a live session keeps growing."""
        earlier = [
            _user("first", timestamp="2026-04-04T18:05:00.000Z"),
            _assistant("answer", timestamp="2026-04-04T18:05:00.000Z"),
        ]
        before = _names_by_first_line(await _turns_of(_write_jsonl(tmp_path, earlier)))

        grown = [*earlier, _user("second", timestamp="2026-04-04T18:06:00.000Z")]
        after = _names_by_first_line(await _turns_of(_write_jsonl(tmp_path, grown)))

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

        paths = [turn.path for turn in await _turns_of(transcript)]

        assert len(set(paths)) == len(paths)


# Two time zones a reader may open the same transcript in, nine hours apart
TIME_ZONES = ("UTC", "Asia/Tokyo")
# A moment in the conversation, and the ids Claude Code gave the entries said then
SAID_AT = "2026-04-04T18:05:44.342Z"
QUESTION_ID = "f260656f-4a3e-4b81-aacb-ae9abb0c7c12"
ANSWER_ID = "a8769bec-5a5d-47b2-9593-153bf1e7f073"


@pytest.fixture
def time_zone(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    """Let a test read in another time zone, and put the machine's back after it."""
    yield monkeypatch
    monkeypatch.undo()
    time.tzset()


async def test_a_turn_is_named_by_the_id_its_transcript_gives_it_in_every_time_zone(
    tmp_path: Path, time_zone: pytest.MonkeyPatch
) -> None:
    """Threads and the unsent draft hang on the name: read in another time zone, the same turn is the same turn."""
    transcript = _write_jsonl(
        tmp_path,
        [
            {**_user("what changed?", timestamp=SAID_AT), "uuid": QUESTION_ID},
            {**_assistant("the parser", timestamp=SAID_AT), "uuid": ANSWER_ID},
        ],
    )
    names_by_zone = []
    for zone in TIME_ZONES:
        time_zone.setenv("TZ", zone)
        time.tzset()
        names_by_zone.append([turn.path for turn in await _turns_of(transcript)])

    assert names_by_zone[0] == names_by_zone[1]
    assert names_by_zone[0] == [f"assistant {ANSWER_ID[:8]}", f"user {QUESTION_ID[:8]}"]

"""Functional requirement tests for a round as the agent reads it, in a review of a conversation.

The agent does not have the conversation in front of it, so each thread
quotes what it is on, with the lines around it, rather than naming a place.
"""

from claude_review.domain.models import (
    FIRST_ROUND,
    CommentSeverity,
    DiffFile,
    ReviewMode,
    ReviewResult,
    Thread,
)
from claude_review.services.anchor_service import AnchorService, LineAnchorHandler, StoryAnchorHandler
from claude_review.services.round_formatter import RoundFormatter
from claude_review.services.whole_file import whole_file
from tests.helpers import line_anchor, thread


def _message(name: str, lines: list[str]) -> DiffFile:
    """One message of the conversation, as the review holds it."""
    return whole_file(name, "\n".join(lines))


def _formatted(threads: list[Thread], body: str | None, files: list[DiffFile]) -> ReviewResult:
    """The round as the agent reads it, in its first round."""
    formatter = RoundFormatter.for_mode(ReviewMode.TRANSCRIPT)
    anchors = AnchorService(lines=LineAnchorHandler(files), story=StoryAnchorHandler(None))
    return formatter.format(threads, body, round_number=FIRST_ROUND, anchors=anchors)


def test_a_review_of_a_conversation_is_headed_as_one() -> None:
    """Non-empty review starts with ## Transcript Review."""
    files = [_message("user-1", ["hello"])]
    threads = [thread(line_anchor("user-1", 1), "Bad idea")]

    result = _formatted(threads, None, files)

    assert result.markdown.startswith("## Transcript Review")


def test_a_conversation_is_quoted_not_numbered() -> None:
    """Output has no ### headings, no line numbers — just blockquotes and threads."""
    files = [_message("user-1", ["hello world"])]
    threads = [thread(line_anchor("user-1", 1), "Fix it")]

    result = _formatted(threads, None, files)

    assert "###" not in result.markdown
    assert ":1" not in result.markdown


def test_how_a_thread_is_meant_to_be_taken_is_said() -> None:
    """A blocker, a settled note and one written against words since gone are different instructions."""
    files = [_message("user-1", ["hello world"])]
    threads = [
        thread(line_anchor("user-1", 1, outdated=True), "Fix it", severity=CommentSeverity.BLOCKER, resolved=True)
    ]

    markdown = _formatted(threads, None, files).markdown

    assert "blocker, resolved, outdated" in markdown


def test_a_comment_quotes_two_lines_either_side_and_no_more() -> None:
    """Enough to read the sentence in what it follows from, not the whole message."""
    files = [_message("assistant-2", [f"line {number}" for number in range(1, 10)])]
    threads = [thread(line_anchor("assistant-2", 5), "Why?")]

    markdown = _formatted(threads, None, files).markdown

    assert "> line 3\n> line 4\n> line 5\n> line 6\n> line 7\nWhy?" in markdown
    assert "> line 2" not in markdown
    assert "> line 8" not in markdown


def test_a_comment_quotes_only_its_own_message() -> None:
    files = [_message("user-1", ["the question"]), _message("assistant-2", ["the answer"])]
    threads = [thread(line_anchor("assistant-2", 1), "Wrong")]

    markdown = _formatted(threads, None, files).markdown

    assert "> the answer" in markdown
    assert "the question" not in markdown


def test_a_comment_on_a_message_the_review_no_longer_holds_is_sent_without_a_quote() -> None:
    """A thread may outlive what it was written on; what was said in it still goes."""
    threads = [thread(line_anchor("assistant-9", 1), "Still matters")]

    markdown = _formatted(threads, None, [_message("user-1", ["hello"])]).markdown

    assert "Still matters" in markdown
    assert ">" not in markdown

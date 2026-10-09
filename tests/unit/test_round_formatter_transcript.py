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
    TurnAuthor,
)
from claude_review.services.anchor_service import AnchorService
from claude_review.services.round_formatter import RoundFormatter
from claude_review.services.whole_file import whole_file
from tests.helpers import line_anchor, thread


def _message(name: str, lines: list[str]) -> DiffFile:
    """One message of the conversation, as the review holds it."""
    return whole_file(name, "\n".join(lines))


def _formatted(threads: list[Thread], body: str | None, files: list[DiffFile]) -> ReviewResult:
    """The round as the agent reads it, in its first round."""
    formatter = RoundFormatter.for_mode(ReviewMode.TRANSCRIPT)
    return formatter.format(threads, body, round_number=FIRST_ROUND, anchors=AnchorService.of_diff(files))


def test_a_review_of_a_conversation_is_headed_as_one() -> None:
    """Non-empty review starts with ## Transcript Review."""
    files = [_message("user-1", ["hello"])]
    threads = [thread(line_anchor("user-1", 1), "Bad idea")]

    result = _formatted(threads, None, files)

    assert result.markdown.startswith("## Transcript Review")


def test_a_comment_quotes_the_lines_around_it() -> None:
    """Comment includes blockquote of surrounding lines."""
    files = [_message("user-1", ["line one", "line two", "line three", "line four", "line five"])]
    threads = [thread(line_anchor("user-1", 3), "This is wrong")]

    result = _formatted(threads, None, files)

    assert "> line one" in result.markdown
    assert "> line two" in result.markdown
    assert "> line three" in result.markdown
    assert "> line four" in result.markdown
    assert "> line five" in result.markdown
    assert "This is wrong" in result.markdown
    assert result.comment_count == 1


def test_a_comment_on_the_first_line_quotes_from_the_start() -> None:
    """Comment on line 1 doesn't crash — context starts at beginning."""
    files = [_message("user-1", ["first line", "second line"])]
    threads = [thread(line_anchor("user-1", 1), "Fix this")]

    result = _formatted(threads, None, files)

    assert "> first line" in result.markdown
    assert "> second line" in result.markdown
    assert "Fix this" in result.markdown


def test_a_comment_on_the_last_line_quotes_to_the_end() -> None:
    """Comment on last line doesn't crash — context ends at message boundary."""
    files = [_message("user-1", ["first", "second", "last"])]
    threads = [thread(line_anchor("user-1", 3), "Fix last")]

    result = _formatted(threads, None, files)

    assert "> first" in result.markdown
    assert "> last" in result.markdown
    assert "Fix last" in result.markdown


def test_the_summary_comes_before_the_comments() -> None:
    """Body text appears before inline threads."""
    files = [_message("user-1", ["hello"])]
    threads = [thread(line_anchor("user-1", 1), "Inline note")]

    result = _formatted(threads, "General feedback here.", files)

    assert result.comment_count == 2
    body_pos = result.markdown.index("General feedback here.")
    inline_pos = result.markdown.index("Inline note")
    assert body_pos < inline_pos


def test_an_empty_summary_is_no_summary() -> None:
    """Empty string body is ignored."""
    files = [_message("user-1", ["hello"])]
    threads = [thread(line_anchor("user-1", 1), "note")]

    result = _formatted(threads, "", files)

    assert result.comment_count == 1


def test_a_review_with_nothing_in_it_says_nothing() -> None:
    """Zero threads and no body produces empty result."""
    result = _formatted([], None, [])

    assert result.comment_count == 0
    assert result.markdown == ""


def test_each_comment_quotes_its_own_message() -> None:
    """Each comment gets its own blockquote context block."""
    files = [
        _message("user-1", ["question about auth"]),
        _message("assistant-2", ["def authenticate(token):", "    return jwt.decode(token)"]),
    ]
    threads = [
        thread(line_anchor("user-1", 1), "Wrong approach"),
        thread(line_anchor("assistant-2", 1, 2), "Don't use JWT"),
    ]

    result = _formatted(threads, None, files)

    assert "> question about auth" in result.markdown
    assert "Wrong approach" in result.markdown
    assert "> def authenticate(token):" in result.markdown
    assert "Don't use JWT" in result.markdown
    assert result.comment_count == 2


def test_a_conversation_is_quoted_not_numbered() -> None:
    """Output has no ### headings, no line numbers — just blockquotes and threads."""
    files = [_message("user-1", ["hello world"])]
    threads = [thread(line_anchor("user-1", 1), "Fix it")]

    result = _formatted(threads, None, files)

    assert "###" not in result.markdown
    assert ":1" not in result.markdown


def test_a_summary_of_only_whitespace_is_no_summary() -> None:
    """Whitespace-only body is ignored, same as empty."""
    files = [_message("user-1", ["hello"])]
    threads = [thread(line_anchor("user-1", 1), "note")]

    result = _formatted(threads, "   \n  ", files)

    assert result.comment_count == 1


def test_a_comment_on_several_lines_quotes_them_all() -> None:
    """A comment on lines 2-4 includes those lines in the blockquote."""
    files = [
        _message(
            "assistant-2",
            [
                "line 1",
                "line 2",
                "line 3",
                "line 4",
                "line 5",
            ],
        )
    ]
    threads = [thread(line_anchor("assistant-2", 2, 4), "Refactor this")]

    result = _formatted(threads, None, files)

    # All 5 lines should be in context (lines 2-4 ± 2)
    assert "> line 1" in result.markdown
    assert "> line 2" in result.markdown
    assert "> line 3" in result.markdown
    assert "> line 4" in result.markdown
    assert "> line 5" in result.markdown
    assert "Refactor this" in result.markdown


def test_how_a_thread_is_meant_to_be_taken_is_said() -> None:
    """A blocker, a settled note and one written against words since gone are different instructions."""
    files = [_message("user-1", ["hello world"])]
    threads = [
        thread(line_anchor("user-1", 1, outdated=True), "Fix it", severity=CommentSeverity.BLOCKER, resolved=True)
    ]

    markdown = _formatted(threads, None, files).markdown

    assert "blocker, resolved, outdated" in markdown


def test_a_thread_the_agent_raised_opens_with_the_agent_speaking() -> None:
    files = [_message("assistant-1", ["I chose JWT"])]
    threads = [thread(line_anchor("assistant-1", 1), "I kept the old flow on purpose", raised_by=TurnAuthor.AUTHOR)]

    markdown = _formatted(threads, None, files).markdown

    assert "> **You:** I kept the old flow on purpose" in markdown

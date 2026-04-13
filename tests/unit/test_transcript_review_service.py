"""Functional tests for TranscriptReviewService.

These test the formatting of transcript review comments into
self-contained markdown that includes context from the conversation.
"""

from claude_review.domain.models import (
    Comment,
    DiffFile,
    DiffHunk,
    DiffLine,
    FileStatus,
    LineType,
)
from claude_review.services.transcript_review_service import TranscriptReviewService


def _make_message(path: str, lines: list[str]) -> DiffFile:
    """Build a DiffFile representing a transcript message."""
    return DiffFile(
        path=path,
        status=FileStatus.ADDED,
        hunks=[
            DiffHunk(
                header="",
                old_start=0,
                new_start=1,
                lines=[
                    DiffLine(type=LineType.CONTEXT, old_no=None, new_no=i, content=line)
                    for i, line in enumerate(lines, start=1)
                ],
            )
        ],
    )


def _service() -> TranscriptReviewService:
    return TranscriptReviewService()


def test_heading_is_transcript_review() -> None:
    """Non-empty review starts with ## Transcript Review."""
    files = [_make_message("user-1", ["hello"])]
    comments = [Comment(file="user-1", start_line=1, end_line=1, body="Bad idea")]

    result = _service().format_review(comments, None, files)

    assert result.markdown.startswith("## Transcript Review")


def test_single_comment_with_context() -> None:
    """Comment includes blockquote of surrounding lines."""
    files = [_make_message("user-1", ["line one", "line two", "line three", "line four", "line five"])]
    comments = [Comment(file="user-1", start_line=3, end_line=3, body="This is wrong")]

    result = _service().format_review(comments, None, files)

    assert "> line one" in result.markdown
    assert "> line two" in result.markdown
    assert "> line three" in result.markdown
    assert "> line four" in result.markdown
    assert "> line five" in result.markdown
    assert "This is wrong" in result.markdown
    assert result.comment_count == 1


def test_context_at_start_of_message() -> None:
    """Comment on line 1 doesn't crash — context starts at beginning."""
    files = [_make_message("user-1", ["first line", "second line"])]
    comments = [Comment(file="user-1", start_line=1, end_line=1, body="Fix this")]

    result = _service().format_review(comments, None, files)

    assert "> first line" in result.markdown
    assert "> second line" in result.markdown
    assert "Fix this" in result.markdown


def test_context_at_end_of_message() -> None:
    """Comment on last line doesn't crash — context ends at message boundary."""
    files = [_make_message("user-1", ["first", "second", "last"])]
    comments = [Comment(file="user-1", start_line=3, end_line=3, body="Fix last")]

    result = _service().format_review(comments, None, files)

    assert "> first" in result.markdown
    assert "> last" in result.markdown
    assert "Fix last" in result.markdown


def test_body_appears_before_comments() -> None:
    """Body text appears before inline comments."""
    files = [_make_message("user-1", ["hello"])]
    comments = [Comment(file="user-1", start_line=1, end_line=1, body="Inline note")]

    result = _service().format_review(comments, "General feedback here.", files)

    assert result.comment_count == 2
    body_pos = result.markdown.index("General feedback here.")
    inline_pos = result.markdown.index("Inline note")
    assert body_pos < inline_pos


def test_empty_body_treated_as_no_body() -> None:
    """Empty string body is ignored."""
    files = [_make_message("user-1", ["hello"])]
    comments = [Comment(file="user-1", start_line=1, end_line=1, body="note")]

    result = _service().format_review(comments, "", files)

    assert result.comment_count == 1


def test_empty_review_produces_minimal_output() -> None:
    """Zero comments and no body produces empty result."""
    result = _service().format_review([], None, [])

    assert result.comment_count == 0
    assert result.markdown == ""


def test_multiple_comments_each_get_blockquote() -> None:
    """Each comment gets its own blockquote context block."""
    files = [
        _make_message("user-1", ["question about auth"]),
        _make_message("assistant-2", ["def authenticate(token):", "    return jwt.decode(token)"]),
    ]
    comments = [
        Comment(file="user-1", start_line=1, end_line=1, body="Wrong approach"),
        Comment(file="assistant-2", start_line=1, end_line=2, body="Don't use JWT"),
    ]

    result = _service().format_review(comments, None, files)

    assert "> question about auth" in result.markdown
    assert "Wrong approach" in result.markdown
    assert "> def authenticate(token):" in result.markdown
    assert "Don't use JWT" in result.markdown
    assert result.comment_count == 2


def test_no_line_numbers_or_headings_in_output() -> None:
    """Output has no ### headings, no line numbers — just blockquotes and comments."""
    files = [_make_message("user-1", ["hello world"])]
    comments = [Comment(file="user-1", start_line=1, end_line=1, body="Fix it")]

    result = _service().format_review(comments, None, files)

    assert "###" not in result.markdown
    assert ":1" not in result.markdown


def test_whitespace_only_body_treated_as_no_body() -> None:
    """Whitespace-only body is ignored, same as empty."""
    files = [_make_message("user-1", ["hello"])]
    comments = [Comment(file="user-1", start_line=1, end_line=1, body="note")]

    result = _service().format_review(comments, "   \n  ", files)

    assert result.comment_count == 1


def test_range_comment_includes_full_range_in_blockquote() -> None:
    """A comment on lines 2-4 includes those lines in the blockquote."""
    files = [
        _make_message(
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
    comments = [Comment(file="assistant-2", start_line=2, end_line=4, body="Refactor this")]

    result = _service().format_review(comments, None, files)

    # All 5 lines should be in context (lines 2-4 ± 2)
    assert "> line 1" in result.markdown
    assert "> line 2" in result.markdown
    assert "> line 3" in result.markdown
    assert "> line 4" in result.markdown
    assert "> line 5" in result.markdown
    assert "Refactor this" in result.markdown

"""Functional requirement tests for the review service.

These test the formatting of comments into markdown for Claude.
"""

from claude_review.domain.models import Comment
from claude_review.services.review_service import ReviewService


def test_single_comment_formats_with_file_and_line() -> None:
    """A single comment produces markdown with ### file:line header."""
    service = _service()
    comments = [Comment(file="src/handler.ts", start_line=42, end_line=42, body="Wrong null check")]

    result = service.format_review(comments)

    assert "### src/handler.ts:42" in result.markdown
    assert "Wrong null check" in result.markdown
    assert result.comment_count == 1


def test_multiline_comment_formats_as_range() -> None:
    """Comment on lines 10-15 produces ### file:10-15."""
    service = _service()
    comments = [Comment(file="src/utils.py", start_line=10, end_line=15, body="Refactor this block")]

    result = service.format_review(comments)

    assert "### src/utils.py:10-15" in result.markdown
    assert "Refactor this block" in result.markdown


def test_multiple_comments_across_files() -> None:
    """All comments appear in output, ordered as given."""
    service = _service()
    comments = [
        Comment(file="src/a.py", start_line=1, end_line=1, body="Fix A"),
        Comment(file="src/b.py", start_line=5, end_line=5, body="Fix B"),
        Comment(file="src/a.py", start_line=20, end_line=25, body="Fix A again"),
    ]

    result = service.format_review(comments)

    assert result.comment_count == 3
    # All comments present
    assert "### src/a.py:1" in result.markdown
    assert "### src/b.py:5" in result.markdown
    assert "### src/a.py:20-25" in result.markdown
    assert "Fix A" in result.markdown
    assert "Fix B" in result.markdown
    assert "Fix A again" in result.markdown

    # Order preserved: A:1 before B:5 before A:20-25
    pos_a1 = result.markdown.index("### src/a.py:1")
    pos_b5 = result.markdown.index("### src/b.py:5")
    pos_a20 = result.markdown.index("### src/a.py:20-25")
    assert pos_a1 < pos_b5 < pos_a20


def test_empty_review_produces_minimal_output() -> None:
    """Zero comments produces empty result."""
    service = _service()

    result = service.format_review([])

    assert result.comment_count == 0
    assert result.markdown == ""


def test_result_starts_with_header() -> None:
    """Non-empty review starts with ## Code Review Comments."""
    service = _service()
    comments = [Comment(file="x.py", start_line=1, end_line=1, body="note")]

    result = service.format_review(comments)

    assert result.markdown.startswith("## Code Review Comments")


def test_body_alone_produces_review_with_summary() -> None:
    """A review with only a body and no inline comments."""
    service = _service()

    result = service.format_review([], body="Wrong approach, let's use a different pattern.")

    assert result.comment_count == 1
    assert "Wrong approach" in result.markdown
    assert result.markdown.startswith("## Code Review Comments")


def test_body_with_inline_comments_appears_first() -> None:
    """Body text appears before inline comments in the output."""
    service = _service()
    comments = [Comment(file="x.py", start_line=1, end_line=1, body="Fix this line")]

    result = service.format_review(comments, body="Generally good, one issue.")

    assert result.comment_count == 2
    body_pos = result.markdown.index("Generally good")
    inline_pos = result.markdown.index("### x.py:1")
    assert body_pos < inline_pos


def test_empty_body_treated_as_no_body() -> None:
    """Empty string body is ignored, same as None."""
    service = _service()
    comments = [Comment(file="x.py", start_line=1, end_line=1, body="note")]

    result = service.format_review(comments, body="")

    assert result.comment_count == 1


def test_whitespace_only_body_treated_as_no_body() -> None:
    """Whitespace-only body is ignored, same as empty."""
    service = _service()
    comments = [Comment(file="x.py", start_line=1, end_line=1, body="note")]

    result = service.format_review(comments, body="   \n  ")

    assert result.comment_count == 1


def test_no_body_no_comments_produces_empty() -> None:
    """No body and no comments produces empty result."""
    service = _service()

    result = service.format_review([], body=None)

    assert result.comment_count == 0
    assert result.markdown == ""


def _service() -> ReviewService:
    return ReviewService()

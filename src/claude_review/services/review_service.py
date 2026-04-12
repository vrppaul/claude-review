"""Service for formatting review comments into markdown."""

from claude_review.domain.models import Comment, ReviewResult


class ReviewService:
    """Formats review comments into markdown for Claude."""

    def format_review(self, comments: list[Comment], body: str | None = None) -> ReviewResult:
        """Convert comments and optional review body into formatted markdown.

        The body (review summary) appears as a paragraph before inline comments,
        matching GitHub's PR review style.
        """
        has_body = bool(body and body.strip())
        count = len(comments) + (1 if has_body else 0)

        if count == 0:
            return ReviewResult(markdown="", comment_count=0)

        parts = ["## Code Review Comments\n"]

        if has_body:
            parts.append(f"{body}\n")

        for comment in comments:
            line_ref = self._format_line_ref(comment)
            parts.append(f"### {comment.file}:{line_ref}\n{comment.body}\n")

        return ReviewResult(
            markdown="\n".join(parts),
            comment_count=count,
        )

    def _format_line_ref(self, comment: Comment) -> str:
        """Format line reference: '42' for single line, '42-47' for range."""
        if comment.start_line == comment.end_line:
            return str(comment.start_line)
        return f"{comment.start_line}-{comment.end_line}"

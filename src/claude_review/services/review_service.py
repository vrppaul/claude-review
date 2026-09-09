"""Service for formatting review comments into markdown."""

from claude_review.domain.models import Comment, CommentSeverity, LineSide, ReviewResult


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
            parts.append(f"### `{comment.file}`:{line_ref}{self._format_severity(comment)}\n{comment.body}\n")

        return ReviewResult(
            markdown="\n".join(parts),
            comment_count=count,
        )

    def _format_severity(self, comment: Comment) -> str:
        """Name the weight of a comment, unless it is an ordinary note.

        A question wants an answer before anything changes and a blocker has
        to be dealt with, which are different instructions from "here is an
        observation" — and only worth saying when they differ from it.
        """
        if comment.severity == CommentSeverity.NOTE:
            return ""
        return f" — {comment.severity}"

    def _format_line_ref(self, comment: Comment) -> str:
        """Format line reference: '42', '42-47', or '42 (removed)'.

        A comment on the old side points at a line the change deleted, so the
        number refers to the file as it was — saying so keeps the reader from
        opening that line in the current file and reading something unrelated.
        """
        span = str(comment.start_line)
        if comment.start_line != comment.end_line:
            span = f"{comment.start_line}-{comment.end_line}"
        if comment.side == LineSide.OLD:
            return f"{span} (removed)"
        return span

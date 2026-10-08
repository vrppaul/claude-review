"""Service for formatting review comments into markdown."""

from claude_review.domain.models import Comment, ReviewResult
from claude_review.services.anchor_service import AnchorService
from claude_review.services.thread_markdown import format_conversation, thread_tags


class ReviewService:
    """Formats review threads into markdown for whoever answers the review."""

    def __init__(self, anchors: AnchorService) -> None:
        self._anchors = anchors

    def format_review(self, comments: list[Comment], body: str | None = None, round_number: int = 1) -> ReviewResult:
        """Convert comments and optional review body into formatted markdown.

        The body (review summary) appears as a paragraph before inline comments,
        matching GitHub's PR review style.
        """
        has_body = bool(body and body.strip())
        count = len(comments) + (1 if has_body else 0)

        if count == 0:
            return ReviewResult(markdown="", comment_count=0)

        parts = [f"{self._format_heading(round_number)}\n"]

        if has_body:
            parts.append(f"{body}\n")

        parts.extend(self._format_comment(comment) for comment in comments)

        return ReviewResult(
            markdown="\n".join(parts),
            comment_count=count,
        )

    def _format_heading(self, round_number: int) -> str:
        """Name the round, once there has been more than one.

        A review sent in one go is just a review; numbering it would say
        there are others when there are not.
        """
        if round_number <= 1:
            return "## Code Review Comments"
        return f"## Code Review Comments — round {round_number}"

    def _format_comment(self, comment: Comment) -> str:
        """Render one thread: its anchor, what was said, and by whom."""
        pieces = [f"### {self._anchors.where(comment.anchor)}{self._format_tags(comment)}"]

        if comment.anchor.outdated and comment.anchor.quote:
            pieces.append(self._format_quote(comment.anchor.quote))

        pieces.extend(format_conversation(comment))

        return "\n".join(pieces) + "\n"

    def _format_quote(self, quote: list[str]) -> str:
        """Carry the lines a comment was written against.

        Once the diff has been retaken those lines may be gone, and a file
        and a line number then point at whatever moved into their place.
        """
        lines = "\n".join(quote)
        return f"Written against these lines, which have since changed:\n\n```\n{lines}\n```\n"

    def _format_tags(self, comment: Comment) -> str:
        tags = thread_tags(comment)
        return f" — {', '.join(tags)}" if tags else ""

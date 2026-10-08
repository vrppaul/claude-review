"""Service for formatting review comments into markdown."""

from claude_review.domain.models import ReviewResult, Thread
from claude_review.services.thread_markdown import format_conversation, thread_tags


class ReviewService:
    """Formats review threads into markdown for whoever answers the review."""

    def format_review(self, threads: list[Thread], body: str | None, round_number: int) -> ReviewResult:
        """Convert threads and optional review body into formatted markdown.

        The body (review summary) appears as a paragraph before inline comments,
        matching GitHub's PR review style.
        """
        has_body = bool(body and body.strip())
        count = len(threads) + (1 if has_body else 0)

        if count == 0:
            return ReviewResult(markdown="", comment_count=0)

        parts = [f"{self._format_heading(round_number)}\n"]

        if has_body:
            parts.append(f"{body}\n")

        parts.extend(self._format_thread(thread) for thread in threads)

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

    def _format_thread(self, thread: Thread) -> str:
        """Render one thread: its anchor, what was said, and by whom."""
        pieces = [f"### {thread.where}{self._format_tags(thread)}"]

        if thread.anchor.outdated and thread.anchor.quote:
            pieces.append(self._format_quote(thread.anchor.quote))

        pieces.extend(format_conversation(thread))

        return "\n".join(pieces) + "\n"

    def _format_quote(self, quote: list[str]) -> str:
        """Carry the lines a comment was written against.

        Once the diff has been retaken those lines may be gone, and a file
        and a line number then point at whatever moved into their place.
        """
        lines = "\n".join(quote)
        return f"Written against these lines, which have since changed:\n\n```\n{lines}\n```\n"

    def _format_tags(self, thread: Thread) -> str:
        tags = thread_tags(thread)
        return f" — {', '.join(tags)}" if tags else ""

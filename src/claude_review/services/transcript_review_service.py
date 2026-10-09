"""Service for formatting transcript review comments into self-contained markdown.

Unlike ReviewService (which formats file:line references for contexts where
Claude already has the code), this formatter includes the actual content as
blockquotes — because Claude won't have the transcript in context when it
reads the review output.
"""

from claude_review.domain.models import DiffFile, ReviewResult, Thread
from claude_review.services.thread_markdown import format_conversation, thread_tags

CONTEXT_LINES = 2


class TranscriptReviewService:
    """Formats transcript review comments into self-contained markdown, quoting the messages they are on."""

    def __init__(self, diff_files: list[DiffFile]) -> None:
        # A conversation is read once and never taken again, so the messages
        # quoted are the ones the review opened on
        self._files_by_path = {file.path: file for file in diff_files}

    def format_review(self, threads: list[Thread], body: str | None, round_number: int) -> ReviewResult:
        """Convert comments and optional body into formatted markdown.

        Each comment is rendered as a blockquote of surrounding context
        around the commented region, followed by the comment body.
        """
        has_body = bool(body and body.strip())
        count = len(threads) + (1 if has_body else 0)

        if count == 0:
            return ReviewResult(markdown="", comment_count=0)

        heading = "## Transcript Review" if round_number <= 1 else f"## Transcript Review — round {round_number}"
        parts = [f"{heading}\n"]

        if has_body:
            parts.append(f"{body}\n")

        for thread in threads:
            context = self._get_context(thread)
            tags = thread_tags(thread)
            said = "\n".join([*([f"_{', '.join(tags)}_"] if tags else []), *format_conversation(thread)])
            parts.append(f"{context}\n{said}\n" if context else f"{said}\n")

        return ReviewResult(
            markdown="\n".join(parts),
            comment_count=count,
        )

    def _get_context(self, thread: Thread) -> str:
        """Extract blockquoted context (±CONTEXT_LINES) around the commented range."""
        anchor = thread.anchor
        file = self._files_by_path.get(anchor.file)
        if not file:
            return ""

        all_lines = [line for hunk in file.hunks for line in hunk.lines]
        if not all_lines:
            return ""

        start = max(0, anchor.start_line - 1 - CONTEXT_LINES)
        end = min(len(all_lines), anchor.end_line + CONTEXT_LINES)

        quoted = [f"> {line.content}" for line in all_lines[start:end]]
        return "\n".join(quoted)

"""Service for formatting transcript review comments into self-contained markdown.

Unlike ReviewService (which formats file:line references for contexts where
Claude already has the code), this formatter includes the actual content as
blockquotes — because Claude won't have the transcript in context when it
reads the review output.
"""

from claude_review.domain.models import Comment, DiffFile, ReviewResult, Turn, TurnAuthor

CONTEXT_LINES = 2

# The agent reading this wrote the change, so its own turns are "You"
TURN_LABELS = {TurnAuthor.AUTHOR: "You", TurnAuthor.READER: "Reviewer"}


def _format_turn(turn: Turn) -> str:
    """Quote one turn of a thread under the comment that opened it."""
    label = f"> **{TURN_LABELS[turn.author]}:**"
    if "\n" not in turn.body:
        return f"{label} {turn.body}"
    quoted = "\n".join(f"> {line}" if line else ">" for line in turn.body.splitlines())
    return f"{label}\n{quoted}"


class TranscriptReviewService:
    """Formats transcript review comments into self-contained markdown."""

    def format_review(
        self,
        comments: list[Comment],
        body: str | None,
        diff_files: list[DiffFile],
        round_number: int = 1,
    ) -> ReviewResult:
        """Convert comments and optional body into formatted markdown.

        Each comment is rendered as a blockquote of surrounding context
        around the commented region, followed by the comment body.
        """
        has_body = bool(body and body.strip())
        count = len(comments) + (1 if has_body else 0)

        if count == 0:
            return ReviewResult(markdown="", comment_count=0)

        files_by_path = {f.path: f for f in diff_files}
        heading = "## Transcript Review" if round_number <= 1 else f"## Transcript Review — round {round_number}"
        parts = [f"{heading}\n"]

        if has_body:
            parts.append(f"{body}\n")

        for comment in comments:
            context = self._get_context(files_by_path, comment)
            said = "\n".join([comment.body, *(_format_turn(turn) for turn in comment.turns)])
            parts.append(f"{context}\n{said}\n" if context else f"{said}\n")

        return ReviewResult(
            markdown="\n".join(parts),
            comment_count=count,
        )

    def _get_context(
        self,
        files_by_path: dict[str, DiffFile],
        comment: Comment,
    ) -> str:
        """Extract blockquoted context (±CONTEXT_LINES) around the commented range."""
        file = files_by_path.get(comment.file)
        if not file:
            return ""

        all_lines = [line for hunk in file.hunks for line in hunk.lines]
        if not all_lines:
            return ""

        start = max(0, comment.start_line - 1 - CONTEXT_LINES)
        end = min(len(all_lines), comment.end_line + CONTEXT_LINES)

        quoted = [f"> {line.content}" for line in all_lines[start:end]]
        return "\n".join(quoted)

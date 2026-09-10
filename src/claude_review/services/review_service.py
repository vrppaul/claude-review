"""Service for formatting review comments into markdown."""

from claude_review.domain.models import Comment, CommentSeverity, LineSide, ReviewResult, Turn, TurnAuthor

# What each side is called in the output. The agent reading this wrote the
# change, so its own turns are addressed to it as "You".
TURN_LABELS = {TurnAuthor.AUTHOR: "You", TurnAuthor.READER: "Reviewer"}


class ReviewService:
    """Formats review threads into markdown for whoever answers the review."""

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
        pieces = [f"### `{comment.file}`:{self._format_line_ref(comment)}{self._format_tags(comment)}"]

        if comment.outdated and comment.quote:
            pieces.append(self._format_quote(comment.quote))

        # A thread the author raised opens with the author speaking, so it
        # is quoted like any other turn: the reader's reply below it then
        # reads as a reply rather than as the whole thread.
        if comment.raised_by == TurnAuthor.AUTHOR:
            pieces.append(self._format_turn(Turn(author=TurnAuthor.AUTHOR, body=comment.body, round=1)))
        else:
            pieces.append(comment.body)
        pieces.extend(self._format_turn(turn) for turn in comment.turns)

        return "\n".join(pieces) + "\n"

    def _format_turn(self, turn: Turn) -> str:
        """Quote a turn under the comment it belongs to, named by its author.

        A blockquote keeps the conversation apart from the comment that
        opened it, so the instruction and the discussion of it do not read
        as one paragraph.
        """
        label = f"> **{TURN_LABELS[turn.author]}:**"
        if "\n" not in turn.body:
            return f"{label} {turn.body}"
        # A quoted block needs the marker on every line, blank ones included
        quoted = "\n".join(f"> {line}" if line else ">" for line in turn.body.splitlines())
        return f"{label}\n{quoted}"

    def _format_quote(self, quote: list[str]) -> str:
        """Carry the lines a comment was written against.

        Once the diff has been retaken those lines may be gone, and a file
        and a line number then point at whatever moved into their place.
        """
        lines = "\n".join(quote)
        return f"Written against these lines, which have since changed:\n\n```\n{lines}\n```\n"

    def _format_tags(self, comment: Comment) -> str:
        """Name what is not ordinary about a comment.

        A question wants an answer before anything changes and a blocker has
        to be dealt with, which are different instructions from "here is an
        observation" — and only worth saying when they differ from it. The
        same goes for a thread that is settled or hanging on lines that moved.
        """
        tags = []
        if comment.severity != CommentSeverity.NOTE:
            tags.append(str(comment.severity))
        if comment.resolved:
            tags.append("resolved")
        if comment.outdated:
            tags.append("outdated")
        return f" — {', '.join(tags)}" if tags else ""

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

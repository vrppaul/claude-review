"""How a thread is written out for the agent, in both review formats."""

from pathlib import Path

from claude_review.domain.models import FIRST_ROUND, CommentSeverity, Thread, Turn, TurnAuthor

# The agent reading this wrote the change, so its own turns are addressed to
# it as "You"
TURN_LABELS = {TurnAuthor.AUTHOR: "You", TurnAuthor.READER: "Reviewer"}
# What starts every line of a Markdown blockquote
QUOTE_MARK = ">"


def format_opening(body: str, images: list[Path]) -> str:
    """What the comment that opened a thread said, as written, with its screenshots."""
    return "\n".join(part for part in (body, *image_lines(images)) if part)


def format_turn(turn: Turn) -> str:
    """Quote a turn under the comment it belongs to, named by its author.

    A blockquote keeps the conversation apart from the comment that opened
    it, so the instruction and the discussion of it do not read as one
    paragraph.
    """
    label = f"{QUOTE_MARK} **{TURN_LABELS[turn.author]}:**"
    lines = [*turn.body.splitlines(), *image_lines(turn.images)]
    if len(lines) == 1:
        return f"{label} {lines[0]}"
    return f"{label}\n{blockquote(lines)}"


def blockquote(lines: list[str]) -> str:
    """The lines as one Markdown blockquote: the mark on every line, blank ones included, or the quote breaks."""
    return "\n".join(f"{QUOTE_MARK} {line}" if line else QUOTE_MARK for line in lines)


def image_lines(images: list[Path]) -> list[str]:
    """Name each screenshot as a file the agent can open."""
    return [f"Image: {path}" for path in images]


def thread_tags(thread: Thread) -> list[str]:
    """What is not ordinary about a thread, and nothing when it is.

    A question wants an answer before anything changes and a blocker has to
    be dealt with, which are different instructions from "here is an
    observation" — and only worth saying when they differ from it. The same
    goes for a thread that is settled or hanging on lines that moved.
    """
    return tags_of(thread.severity, resolved=thread.resolved, outdated=thread.anchor.outdated)


def tags_of(severity: CommentSeverity, *, resolved: bool, outdated: bool) -> list[str]:
    """The tags a thread of this severity and standing carries, wherever it is listed."""
    tags = [str(severity)] if severity != CommentSeverity.NOTE else []
    if resolved:
        tags.append("resolved")
    if outdated:
        tags.append("outdated")
    return tags


def format_conversation(thread: Thread) -> list[str]:
    """Everything said in a thread, the comment that opened it first.

    A thread the author raised opens with the author speaking, so it is
    quoted like any other turn: the reader's reply below it then reads as a
    reply rather than as the whole thread.
    """
    if thread.raised_by == TurnAuthor.AUTHOR:
        opening = format_turn(Turn(author=TurnAuthor.AUTHOR, body=thread.body, round=FIRST_ROUND, images=thread.images))
    else:
        opening = format_opening(thread.body, thread.images)
    return [opening, *(format_turn(turn) for turn in thread.turns)]

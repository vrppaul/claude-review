"""How a thread is written out for the agent, in both review formats."""

from pathlib import Path

from claude_review.domain.models import FIRST_ROUND, CommentSeverity, Thread, Turn, TurnAuthor

# The agent reading this wrote the change, so its own turns are addressed to
# it as "You"
TURN_LABELS = {TurnAuthor.AUTHOR: "You", TurnAuthor.READER: "Reviewer"}
# What starts every line of a Markdown blockquote, and a quoted line that says something
QUOTE_MARK = ">"
QUOTED_LINE = f"{QUOTE_MARK} {{line}}"
# How a turn is headed: who said it, in bold, inside the quote. A turn of one
# line follows its label; a longer one is quoted below it.
TURN_LABEL = f"{QUOTE_MARK} **{{author}}:**"
ONE_LINE_TURN = "{label} {line}"
LONGER_TURN = "{label}\n{quote}"
# How a screenshot is named, as a file the agent can open
IMAGE_LINE = "Image: {path}"
# What a thread is tagged with once settled, and once the lines it hangs on are gone
RESOLVED_TAG = "resolved"
OUTDATED_TAG = "outdated"
# What ends each line written out
LINE_SEPARATOR = "\n"


def format_opening(body: str, images: list[Path]) -> str:
    """What the comment that opened a thread said, as written, with its screenshots."""
    return LINE_SEPARATOR.join(part for part in (body, *image_lines(images)) if part)


def format_turn(turn: Turn) -> str:
    """Quote a turn under the comment it belongs to, named by its author.

    A blockquote keeps the conversation apart from the comment that opened
    it, so the instruction and the discussion of it do not read as one
    paragraph.
    """
    label = TURN_LABEL.format(author=TURN_LABELS[turn.author])
    lines = [*turn.body.splitlines(), *image_lines(turn.images)]
    if len(lines) == 1:
        return ONE_LINE_TURN.format(label=label, line=lines[0])
    return LONGER_TURN.format(label=label, quote=blockquote(lines))


def blockquote(lines: list[str]) -> str:
    """The lines as one Markdown blockquote: the mark on every line, blank ones included, or the quote breaks."""
    return LINE_SEPARATOR.join(QUOTED_LINE.format(line=line) if line else QUOTE_MARK for line in lines)


def image_lines(images: list[Path]) -> list[str]:
    """Name each screenshot as a file the agent can open."""
    return [IMAGE_LINE.format(path=path) for path in images]


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
        tags.append(RESOLVED_TAG)
    if outdated:
        tags.append(OUTDATED_TAG)
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

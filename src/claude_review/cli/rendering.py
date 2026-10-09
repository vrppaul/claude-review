"""How a review already under way is laid out for an agent catching up on it.

An index first — a line per thread, the panel in short — because handing
over the whole review unasked would cost more than the work; a thread in
full when it is named.
"""

from claude_review.domain.models import Thread, TurnAuthor
from claude_review.presentation.schemas import ContextResponse, ThreadSummary
from claude_review.services.thread_markdown import tags_of

# How much of a comment fits on one line of an index without becoming the index
GIST_LENGTH = 72
# What stands in for the rest of a line cut short
ELLIPSIS = "…"
# How each side of the review is named to the agent reading it, which is
# "you" here as it is in the skill: what it raised is "yours"
SPEAKERS = {TurnAuthor.READER: "reader", TurnAuthor.AUTHOR: "you"}
RAISED_BY_THE_AGENT = "yours"
# How deep what belongs to a line of the index is set under it
INDENT = "  "
MARK_SEPARATOR = " · "
# What stands between who said something, or what it is, and what was said
LABEL_SEPARATOR = ": "

# The words the index and a thread are laid out with
ROUND_LABEL = "round"
NOBODY_ANSWERING = "nobody answering"
OPEN_LABEL = "open"
PANEL_HEADING = "panel:"
# What a message that is an image alone says, where an empty line says nothing
IMAGE_ONLY = "(image)"
IMAGE_LABEL = "image"
QUOTE_LABEL = "lines"
# The things the index counts, each named in the singular
FILE_NOUN = "file"
THREAD_NOUN = "thread"
MESSAGE_NOUN = "message"
TURN_NOUN = "turn"


def render_context(seen: ContextResponse) -> str:
    """Lay the review out for reading, in as few lines as it can be said: one per thread, the panel in short."""
    open_count = sum(1 for summary in seen.threads if not summary.resolved and not summary.outdated)
    heading = [seen.title, f"{ROUND_LABEL} {seen.round}", _counted(seen.file_count, FILE_NOUN)]
    if not seen.answerer_attached:
        heading.append(NOBODY_ANSWERING)
    lines = [
        MARK_SEPARATOR.join(heading),
        MARK_SEPARATOR.join(
            [
                f"{_counted(len(seen.threads), THREAD_NOUN)}, {open_count} {OPEN_LABEL}",
                f"{PANEL_HEADING} {_counted(len(seen.panel), MESSAGE_NOUN)}",
            ]
        ),
    ]

    for summary in seen.threads:
        lines.append("")
        lines.append(f"{summary.thread_id}  {summary.where}  {_marks(summary)}")
        lines.append(_indent(_gist(summary.body)))

    if seen.panel:
        lines.append("")
        lines.append(PANEL_HEADING)
        for entry in seen.panel:
            said = _gist(entry.body) or (IMAGE_ONLY if entry.images else "")
            lines.append(_indent(said, who=SPEAKERS[entry.author]))
            lines.extend(f"{INDENT * 2}{IMAGE_LABEL}{LABEL_SEPARATOR}{path}" for path in entry.images)

    return "\n".join(lines)


def render_thread(thread: Thread) -> str:
    """One thread in full: everything said in it, and the lines it hangs on."""
    lines = [f"{thread.thread_id}  {thread.where}  {_marks(ThreadSummary.of(thread))}"]
    lines.append(_indent(thread.body))
    lines.extend(_indent(turn.body, who=SPEAKERS[turn.author]) for turn in thread.turns)
    if thread.anchor.quote:
        lines.append(_indent("\n".join(thread.anchor.quote), who=QUOTE_LABEL))
    return "\n".join(lines)


def _marks(summary: ThreadSummary) -> str:
    """What is not ordinary about a thread, and nothing when it is."""
    marks = tags_of(summary.severity, resolved=summary.resolved, outdated=summary.outdated)
    if summary.raised_by == TurnAuthor.AUTHOR:
        marks.append(RAISED_BY_THE_AGENT)
    if summary.turn_count:
        marks.append(_counted(summary.turn_count, TURN_NOUN))
    return MARK_SEPARATOR.join(marks)


def _indent(text: str, *, who: str | None = None) -> str:
    """Set every line of something said under the line it belongs to, with who said it."""
    label = f"{who}{LABEL_SEPARATOR}" if who else ""
    return "\n".join(f"{INDENT}{label}{line}" for line in text.splitlines()) or f"{INDENT}{label}"


def _gist(text: str) -> str:
    """The first line of something, short enough to scan a list of them."""
    first = text.strip().splitlines()[0] if text.strip() else ""
    return first if len(first) <= GIST_LENGTH else f"{first[: GIST_LENGTH - len(ELLIPSIS)]}{ELLIPSIS}"


def _counted(count: int, noun: str) -> str:
    """A count with its noun, singular for one: "1 file", "3 files"."""
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"

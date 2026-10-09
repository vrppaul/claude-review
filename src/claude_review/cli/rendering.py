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
# What a message that is an image alone says in the index, where an empty line says nothing
IMAGE_ONLY = "(image)"
# How each side of the panel is named to the agent reading it
SPEAKERS = {TurnAuthor.READER: "you", TurnAuthor.AUTHOR: "me"}
# How deep what belongs to a line of the index is set under it
INDENT = "  "
MARK_SEPARATOR = " · "


def render_context(seen: ContextResponse) -> str:
    """Lay the review out for reading, in as few lines as it can be said: one per thread, the panel in short."""
    open_count = sum(1 for summary in seen.threads if not summary.resolved and not summary.outdated)
    lines = [
        MARK_SEPARATOR.join(
            [
                seen.title,
                f"round {seen.round}",
                _counted(seen.file_count, "file"),
                *([] if seen.answerer_attached else ["nobody answering"]),
            ]
        ),
        f"{_counted(len(seen.threads), 'thread')}, {open_count} open · panel: {_counted(len(seen.panel), 'message')}",
    ]

    for summary in seen.threads:
        lines.append("")
        lines.append(f"{summary.thread_id}  {summary.where}  {_marks(summary)}")
        lines.append(_indent(_gist(summary.body)))

    if seen.panel:
        lines.append("")
        lines.append("panel:")
        for entry in seen.panel:
            lines.append(f"{INDENT}{SPEAKERS[entry.author]}: {_gist(entry.body) or IMAGE_ONLY}")
            lines.extend(f"{INDENT * 2}image: {path}" for path in entry.images)

    return "\n".join(lines)


def render_thread(thread: Thread) -> str:
    """One thread in full: everything said in it, and the lines it hangs on."""
    lines = [f"{thread.thread_id}  {thread.where}  {_marks(ThreadSummary.of(thread))}"]
    lines.append(_indent(thread.body))
    lines.extend(_indent(turn.body, who=turn.author) for turn in thread.turns)
    if thread.anchor.quote:
        lines.append(_indent("\n".join(thread.anchor.quote), who="lines"))
    return "\n".join(lines)


def _marks(summary: ThreadSummary) -> str:
    """What is not ordinary about a thread, and nothing when it is."""
    marks = tags_of(summary.severity, resolved=summary.resolved, outdated=summary.outdated)
    if summary.raised_by == TurnAuthor.AUTHOR:
        marks.append("yours")
    if summary.turn_count:
        marks.append(_counted(summary.turn_count, "turn"))
    return MARK_SEPARATOR.join(marks)


def _indent(text: str, *, who: str | None = None) -> str:
    """Set every line of something said under the line it belongs to, with who said it."""
    label = f"{who}: " if who else ""
    return "\n".join(f"{INDENT}{label}{line}" for line in text.splitlines()) or f"{INDENT}{label}"


def _gist(text: str) -> str:
    """The first line of something, short enough to scan a list of them."""
    first = text.strip().splitlines()[0] if text.strip() else ""
    return first if len(first) <= GIST_LENGTH else f"{first[: GIST_LENGTH - len(ELLIPSIS)]}{ELLIPSIS}"


def _counted(count: int, noun: str) -> str:
    """A count with its noun, singular for one: "1 file", "3 files"."""
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"

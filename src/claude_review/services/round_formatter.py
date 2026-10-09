"""A round written out for the agent: a heading, the reader's summary, then every thread.

What a thread is written against depends on what the agent has in front of
it. In a review of a diff or of files it has the files: a thread is headed
by its place, and carries the lines it was written against once they have
moved. In a review of a conversation it does not: a thread quotes what it
is on, with the lines around it. Each kind of review leads into its threads
its own way; the round around them is the same.
"""

from typing import Protocol, Self

from claude_review.domain.models import FIRST_ROUND, ReviewMode, ReviewResult, Thread
from claude_review.services.anchor_service import AnchorService
from claude_review.services.place_words import place_in_markdown
from claude_review.services.thread_markdown import format_conversation, thread_tags

# How many lines either side of a thread's own a conversation's round
# quotes, so a comment on one sentence is read with the ones it follows from
EXCERPT_REACH = 2
TAG_SEPARATOR = ", "


class ThreadLead(Protocol):
    """How a round leads into each thread, for one kind of review."""

    @property
    def title(self) -> str:
        """What the round is headed as."""
        ...

    def lead(self, thread: Thread, anchors: AnchorService) -> list[str]:
        """What comes before everything said in the thread."""
        ...


class PlaceLead:
    """The agent has the files: name the place, and carry the old lines once they have moved."""

    @property
    def title(self) -> str:
        return "Code Review Comments"

    def lead(self, thread: Thread, anchors: AnchorService) -> list[str]:
        tags = thread_tags(thread)
        tagged = f" — {TAG_SEPARATOR.join(tags)}" if tags else ""
        heading = f"### {place_in_markdown(thread.anchor)}{tagged}"
        if thread.anchor.outdated and thread.anchor.quote:
            return [heading, _written_against(thread.anchor.quote)]
        return [heading]


class ExcerptLead:
    """The agent does not have the conversation: quote what each thread is on, with the lines around it."""

    @property
    def title(self) -> str:
        return "Transcript Review"

    def lead(self, thread: Thread, anchors: AnchorService) -> list[str]:
        excerpt = anchors.excerpt(thread.anchor, reach=EXCERPT_REACH)
        tags = thread_tags(thread)
        lead: list[str] = []
        if excerpt:
            lead.append("\n".join(f"> {line}" for line in excerpt))
        if tags:
            lead.append(f"_{TAG_SEPARATOR.join(tags)}_")
        return lead


# How each kind of review leads into its threads
LEADS: dict[ReviewMode, ThreadLead] = {
    ReviewMode.DIFF: PlaceLead(),
    ReviewMode.FILES: PlaceLead(),
    ReviewMode.TRANSCRIPT: ExcerptLead(),
}


class RoundFormatter:
    """Writes a round out as Markdown for whoever answers the review."""

    def __init__(self, lead: ThreadLead) -> None:
        self._lead = lead

    @classmethod
    def for_mode(cls, mode: ReviewMode) -> Self:
        """The formatter for one kind of review."""
        return cls(LEADS[mode])

    def format(
        self, threads: list[Thread], body: str | None, *, round_number: int, anchors: AnchorService
    ) -> ReviewResult:
        """The round as Markdown: the summary, when there is one, before the threads.

        `anchors` are the take of the content the threads were written on.
        A summary of nothing but whitespace is no summary; a round with
        neither is empty, and says nothing.
        """
        summary = body if body and body.strip() else None
        count = len(threads) + (1 if summary else 0)
        if count == 0:
            return ReviewResult(markdown="", comment_count=0)

        parts = [f"{self._heading(round_number)}\n"]
        if summary:
            parts.append(f"{summary}\n")
        parts.extend(self._thread(thread, anchors) for thread in threads)
        return ReviewResult(markdown="\n".join(parts), comment_count=count)

    def _heading(self, round_number: int) -> str:
        """Name the round, once there has been more than one.

        A review sent in one go is just a review; numbering it would say
        there are others when there are not.
        """
        title = f"## {self._lead.title}"
        return title if round_number <= FIRST_ROUND else f"{title} — round {round_number}"

    def _thread(self, thread: Thread, anchors: AnchorService) -> str:
        return "\n".join([*self._lead.lead(thread, anchors), *format_conversation(thread)]) + "\n"


def _written_against(quote: list[str]) -> str:
    """The lines a comment was written against.

    Once the diff has been retaken those lines may be gone, and a file and a
    line number then point at whatever moved into their place.
    """
    lines = "\n".join(quote)
    return f"Written against these lines, which have since changed:\n\n```\n{lines}\n```\n"

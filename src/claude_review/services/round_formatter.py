"""A round written out for the agent: a heading, the reader's summary, then every thread.

What a thread is written against depends on what the agent has in front of
it. In a review of a diff or of files it has the files: a thread is headed
by its place, and carries the lines it was written against once they have
moved. In a review of a conversation it does not: a thread quotes what it
is on, with the lines around it. Each kind of review leads into its threads
its own way; the round around them is the same.
"""

from abc import ABC, abstractmethod
from typing import Self, override

from claude_review.domain.models import FIRST_ROUND, ReviewMode, ReviewResult, Thread
from claude_review.services.anchor_service import AnchorService
from claude_review.services.markdown_code import code_block
from claude_review.services.place_words import place_in_markdown
from claude_review.services.thread_markdown import blockquote, format_conversation, thread_tags

# What a round is headed as, by what the agent has in front of it
FILES_ROUND_TITLE = "Code Review Comments"
CONVERSATION_ROUND_TITLE = "Transcript Review"
# Markdown's marks for a round's heading and for each thread's
ROUND_HEADING = "##"
THREAD_HEADING = "###"
# What sets an aside — a round's number, a thread's tags — apart from what it is said of
ASIDE = " — "
TAG_SEPARATOR = ", "
# Markdown's mark for words set apart, as a thread's tags are when no heading carries them
EMPHASIS = "_"
# What a round is called after its title, once there has been more than one
ROUND_NUMBERED = "round {number}"
# What a thread whose lines have moved says above the lines it was written against
WRITTEN_AGAINST = "Written against these lines, which have since changed:"
# What ends a line of Markdown, and what ends a paragraph: an empty line after it
LINE_END = "\n"
PARAGRAPH_END = "\n\n"


class ThreadLead(ABC):
    """How a round leads into each thread, for one kind of review."""

    @property
    @abstractmethod
    def title(self) -> str:
        """What the round is headed as."""

    @abstractmethod
    def lead(self, thread: Thread, anchors: AnchorService) -> list[str]:
        """What comes before everything said in the thread."""


class PlaceLead(ThreadLead):
    """The agent has the files: name the place, and carry the old lines once they have moved."""

    @property
    @override
    def title(self) -> str:
        return FILES_ROUND_TITLE

    @override
    def lead(self, thread: Thread, anchors: AnchorService) -> list[str]:
        tags = thread_tags(thread)
        tagged = f"{ASIDE}{TAG_SEPARATOR.join(tags)}" if tags else ""
        heading = f"{THREAD_HEADING} {place_in_markdown(thread.anchor)}{tagged}"
        if thread.anchor.outdated and thread.anchor.quote:
            return [heading, _written_against(thread.anchor.quote)]
        return [heading]


class ExcerptLead(ThreadLead):
    """The agent does not have the conversation: quote what each thread is on, with the lines around it."""

    @property
    @override
    def title(self) -> str:
        return CONVERSATION_ROUND_TITLE

    @override
    def lead(self, thread: Thread, anchors: AnchorService) -> list[str]:
        excerpt = anchors.excerpt(thread.anchor)
        tags = thread_tags(thread)
        lead: list[str] = []
        if excerpt:
            lead.append(blockquote(excerpt))
        if tags:
            lead.append(f"{EMPHASIS}{TAG_SEPARATOR.join(tags)}{EMPHASIS}")
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

        parts = [self._heading(round_number) + LINE_END]
        if summary:
            parts.append(summary + LINE_END)
        parts.extend(self._thread(thread, anchors) for thread in threads)
        return ReviewResult(markdown=LINE_END.join(parts), comment_count=count)

    def _heading(self, round_number: int) -> str:
        """Name the round, once there has been more than one.

        A review sent in one go is just a review; numbering it would say
        there are others when there are not.
        """
        title = f"{ROUND_HEADING} {self._lead.title}"
        return title if round_number <= FIRST_ROUND else f"{title}{ASIDE}{ROUND_NUMBERED.format(number=round_number)}"

    def _thread(self, thread: Thread, anchors: AnchorService) -> str:
        return LINE_END.join([*self._lead.lead(thread, anchors), *format_conversation(thread)]) + LINE_END


def _written_against(quote: list[str]) -> str:
    """The lines a comment was written against, fenced so that no line of them closes the fence.

    Once the diff has been retaken those lines may be gone, and a file and a
    line number then point at whatever moved into their place.
    """
    return f"{WRITTEN_AGAINST}{PARAGRAPH_END}{code_block(quote)}{LINE_END}"

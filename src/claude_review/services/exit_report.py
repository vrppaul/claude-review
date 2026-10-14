"""What a review writes out as it ends: the last round, and whatever the agent never took.

The process stops a moment after the review ends, and an agent busy
answering may not ask for anything in that moment. What it has not read
would go with the process; written to the log instead, it is where the
agent already looks once it hears the review is over.
"""

from typing import assert_never

from claude_review.domain.models import (
    PanelCancel,
    PanelMessage,
    RoundSubmission,
    SaidToTheAgent,
    StoryCancelled,
    ThreadQuestion,
)
from claude_review.services.place_words import place_in_markdown
from claude_review.services.thread_markdown import format_opening

# What heads whatever the agent never took, after the rounds
UNREAD_HEADING = "## Left unread when the review ended"
# How each thing it never took is headed, as deep as a round's own threads
QUESTION_HEADING = "### Question in {thread_id}, {place}"
MESSAGE_HEADING = "### Message {message_id}"
TAKEN_BACK_HEADING = "### Message {message_id} taken back"
# How a panel message names each thread it points at
POINTED_AT = "About {thread_id}, {place}"
# What parts the report — a round, the heading, each thing never taken — and
# the lines of one part
PART_SEPARATOR = "\n\n"
LINE_SEPARATOR = "\n"


def exit_report(last_round: RoundSubmission | None, unread: list[SaidToTheAgent]) -> str:
    """The rounds the agent has not read, or the last one if it has; then anything else it never took.

    The rounds are the review itself, and come first as they always have:
    a review nobody answered prints exactly what it printed before. The
    last round is written even once read, because the agent is told to
    look for it here. The word to stop a story is written nowhere: it holds
    nothing the reader wrote, and the review the story would have been told
    of is over.
    """
    unread_rounds = [event.markdown for event in unread if isinstance(event, RoundSubmission)]
    rounds = unread_rounds or ([last_round.markdown] if last_round is not None else [])
    others = [
        _unread(event) for event in _not_taken_back(unread) if not isinstance(event, RoundSubmission | StoryCancelled)
    ]
    return PART_SEPARATOR.join([*rounds, *([UNREAD_HEADING, *others] if others else [])])


def _not_taken_back(unread: list[SaidToTheAgent]) -> list[SaidToTheAgent]:
    """What is still meant: a message the reader took back goes, and so does the taking back.

    A withdrawal of a message the agent did read stays, because it may
    already be at work on it.
    """
    unread_messages = {event.message_id for event in unread if isinstance(event, PanelMessage)}
    withdrawn = {event.message_id for event in unread if isinstance(event, PanelCancel)} & unread_messages
    return [
        event
        for event in unread
        if not (isinstance(event, PanelMessage | PanelCancel) and event.message_id in withdrawn)
    ]


def _unread(event: ThreadQuestion | PanelMessage | PanelCancel) -> str:
    """One thing the agent never took, as it would have read it."""
    match event:
        case ThreadQuestion():
            heading = QUESTION_HEADING.format(
                thread_id=event.thread.thread_id, place=place_in_markdown(event.thread.anchor)
            )
            return LINE_SEPARATOR.join([heading, format_opening(event.body, event.images)])
        case PanelMessage():
            heading = MESSAGE_HEADING.format(message_id=event.message_id)
            threads = [
                POINTED_AT.format(thread_id=thread.thread_id, place=place_in_markdown(thread.anchor))
                for thread in event.threads
            ]
            return LINE_SEPARATOR.join([heading, format_opening(event.body, event.images), *threads])
        case PanelCancel():
            return TAKEN_BACK_HEADING.format(message_id=event.message_id)
        case _:
            assert_never(event)

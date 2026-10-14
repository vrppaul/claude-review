"""What a review writes out as it ends: the review itself, and whatever the agent never took."""

from pathlib import Path

from claude_review.domain.models import (
    PanelCancel,
    PanelMessage,
    RoundSubmission,
    StoryCancelled,
    ThreadQuestion,
)
from claude_review.services.exit_report import UNREAD_HEADING, exit_report
from tests.helpers import REVIEWED_FILE, line_anchor, thread

LAST_ROUND = RoundSubmission(number=2, markdown="## Code Review Comments — round 2\n\nRename it.", comment_count=1)
A_MESSAGE = PanelMessage(
    message_id="panel-3",
    body="Also check the docs.",
    threads=[thread(line_anchor(REVIEWED_FILE, 1), "This one")],
    images=[Path("/tmp/images/shot.png")],
)


def test_a_review_nobody_answered_writes_only_the_review() -> None:
    """The plain flow: one send, read on stdout, exactly as before."""
    assert exit_report(LAST_ROUND, [LAST_ROUND]) == LAST_ROUND.markdown


def test_the_last_round_is_written_even_once_the_agent_has_read_it() -> None:
    """The agent is told to look for it here."""
    assert exit_report(LAST_ROUND, []) == LAST_ROUND.markdown


def test_what_the_agent_never_took_follows_the_review() -> None:
    written = exit_report(LAST_ROUND, [A_MESSAGE, LAST_ROUND])

    review, unread = written.split(UNREAD_HEADING)
    assert review.strip() == LAST_ROUND.markdown
    assert "Also check the docs." in unread
    assert "/tmp/images/shot.png" in unread
    assert f"`{REVIEWED_FILE}`:1" in unread


def test_a_message_taken_back_before_the_agent_read_it_is_left_out() -> None:
    """Written out, it would invite the agent to act on what the reader withdrew."""
    written = exit_report(LAST_ROUND, [A_MESSAGE, LAST_ROUND, PanelCancel(message_id=A_MESSAGE.message_id)])

    assert written == LAST_ROUND.markdown


def test_a_message_the_agent_read_and_the_reader_then_took_back_says_so() -> None:
    """The agent may already be at work on it."""
    unread = exit_report(LAST_ROUND, [PanelCancel(message_id="panel-2")]).split(UNREAD_HEADING)[1]

    assert "panel-2 taken back" in unread


def test_an_unanswered_question_says_which_thread_it_was_asked_in() -> None:
    asked = thread(line_anchor(REVIEWED_FILE, 1), "Why one?")
    question = ThreadQuestion(question_id="turn-2", body="Still unsure", images=[], thread=asked)

    unread = exit_report(None, [question]).split(UNREAD_HEADING)[1]

    assert asked.thread_id in unread
    assert "Still unsure" in unread


def test_a_story_stopped_that_no_agent_was_told_of_is_no_part_of_what_is_written() -> None:
    """It holds no word the reader wrote, and nobody is left to tell a story to. A story asked for never waits
    among what is unread: the review keeps it, not the agent's inbox."""
    assert exit_report(LAST_ROUND, [StoryCancelled()]) == LAST_ROUND.markdown


def test_a_review_that_sent_nothing_writes_nothing() -> None:
    assert exit_report(None, []) == ""

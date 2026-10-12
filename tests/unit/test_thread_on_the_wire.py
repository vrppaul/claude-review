"""Functional requirement tests for a thread as the agent is handed it: it says, in plain words, where it hangs.

The agent reads a thread as text, often without the file in front of it, so
the thread says its place in words beside the anchor that holds it. The
words are the anchor's, said again: a thread cannot say one place and hang
on another.
"""

from pathlib import Path

from claude_review.domain.models import LineSide, ThreadQuestion
from claude_review.presentation.wire import agent
from claude_review.presentation.wire.threads import Thread
from tests.helpers import line_anchor, thread

ON_REMOVED_LINES = thread(line_anchor("src/a.py", 42, 47, side=LineSide.OLD), "Why were these dropped?")
WHERE_IT_HANGS = "src/a.py:42-47 (removed)"
ELSEWHERE = "src/b.py:1"
# Where a screenshot pasted into a thread is kept: named, never opened here
A_SCREENSHOT = Path("/reviews/images/shot.png")


def test_a_thread_handed_to_the_agent_says_where_it_hangs() -> None:
    assert Thread.of(ON_REMOVED_LINES).where == WHERE_IT_HANGS


def test_a_thread_inside_a_question_says_where_it_hangs_as_one_handed_over_alone_does() -> None:
    asked = ThreadQuestion(
        question_id=ON_REMOVED_LINES.thread_id, body=ON_REMOVED_LINES.body, images=[], thread=ON_REMOVED_LINES
    )

    assert agent.ThreadQuestion.of(asked).thread.where == WHERE_IT_HANGS


def test_where_a_thread_hangs_is_written_out_with_it() -> None:
    """Whoever reads the thread as JSON reads the words too, without working them out from the anchor."""
    assert Thread.of(ON_REMOVED_LINES).model_dump()["where"] == WHERE_IT_HANGS


def test_a_thread_says_where_its_anchor_is_whatever_place_it_was_sent_with() -> None:
    """Said from the anchor each time, never kept beside it: the two cannot come to disagree."""
    sent = Thread.of(ON_REMOVED_LINES).model_dump() | {"where": ELSEWHERE}

    assert Thread.model_validate(sent).where == WHERE_IT_HANGS


def test_a_thread_read_back_from_its_own_json_is_the_thread_that_was_written() -> None:
    """A command reads what the review wrote: nothing of a thread is lost on the way, its screenshots among it."""
    with_a_screenshot = thread(line_anchor("src/a.py", 42), "See the picture.", images=[A_SCREENSHOT])
    written = Thread.of(with_a_screenshot)

    assert Thread.model_validate_json(written.model_dump_json()) == written

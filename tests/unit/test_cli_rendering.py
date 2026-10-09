"""How a review under way reads to an agent catching up on it: an index first, a thread in full when named."""

from pathlib import Path

from claude_review.cli.rendering import GIST_LENGTH, render_context, render_thread
from claude_review.domain.models import AgentStatus, CommentSeverity, PanelEntry, Turn, TurnAuthor
from claude_review.presentation.schemas import ContextResponse, ThreadSummary
from tests.helpers import line_anchor, thread

SAID_AT = 1

# A thread as the server holds it, so this reads what the agent is handed
DISCUSSED = thread(
    line_anchor("src/routes.py", 118, 130, quote=["    return event"]),
    "Does a round overtake a question?\nAnd if it does, what then?",
    thread_id="comment-4",
    severity=CommentSeverity.QUESTION,
    turns=[Turn(author=TurnAuthor.AUTHOR, body="It cannot: one queue.", round=2)],
)
SETTLED = thread(line_anchor("src/app.py", 3), "Rename it", thread_id="comment-5", resolved=True)
GONE = thread(line_anchor("src/old.py", 9, outdated=True), "This moved", thread_id="comment-6")
RAISED = thread(line_anchor("src/app.py", 7), "Kept on purpose", thread_id="raised-1", raised_by=TurnAuthor.AUTHOR)

ASKED_TO_RUN_THE_TESTS = PanelEntry(message_id="panel-1", author=TurnAuthor.READER, body="Run the tests", at=SAID_AT)

SEEN = ContextResponse(
    title="claude-review: uncommitted changes",
    round=3,
    file_count=7,
    answerer_attached=True,
    agent=AgentStatus(model="opus-5", context="45% of 1M", at=SAID_AT),
    threads=[ThreadSummary.of(DISCUSSED)],
    panel=[ASKED_TO_RUN_THE_TESTS],
)


def _line_of(printed: str, thread_id: str) -> str:
    [found] = [line for line in printed.splitlines() if line.startswith(thread_id)]
    return found


def test_catching_up_costs_a_line_a_thread() -> None:
    """An index is what makes catching up cheaper than being handed the review."""
    printed = render_context(SEEN)

    assert "round 3 · 7 files" in printed
    assert "`src/routes.py`:118-130" in _line_of(printed, "comment-4")
    assert "question" in _line_of(printed, "comment-4")
    # The first line of the comment, and not the second
    assert "Does a round overtake a question?" in printed
    assert "And if it does" not in printed


def test_only_threads_still_to_settle_count_as_open() -> None:
    """Settled and outdated threads are history; the count says what is left to do."""
    threads = [ThreadSummary.of(each) for each in (DISCUSSED, SETTLED, GONE)]

    printed = render_context(SEEN.model_copy(update={"threads": threads}))

    assert "3 threads, 1 open" in printed


def test_one_of_anything_is_counted_as_one() -> None:
    printed = render_context(SEEN.model_copy(update={"file_count": 1}))

    assert printed.splitlines()[0].endswith("round 3 · 1 file")
    assert "1 thread, 1 open" in printed
    assert "panel: 1 message" in printed
    assert "1 turn" in _line_of(printed, "comment-4")


def test_what_is_not_ordinary_about_a_thread_is_marked_on_its_line() -> None:
    """Settled, outdated, raised by the agent: each changes what a thread asks of it."""
    threads = [ThreadSummary.of(each) for each in (SETTLED, GONE, RAISED)]

    printed = render_context(SEEN.model_copy(update={"threads": threads}))

    assert "resolved" in _line_of(printed, "comment-5")
    assert "outdated" in _line_of(printed, "comment-6")
    assert "yours" in _line_of(printed, "raised-1")


def test_a_long_comment_is_cut_to_one_line_of_the_index() -> None:
    long = thread(line_anchor("src/app.py", 1), "word " * GIST_LENGTH, thread_id="comment-7")

    printed = render_context(SEEN.model_copy(update={"threads": [ThreadSummary.of(long)]}))
    [gist] = [line.strip() for line in printed.splitlines() if line.strip().startswith("word")]

    assert len(gist) == GIST_LENGTH
    assert gist.endswith("…")


def test_a_thread_asked_for_by_name_comes_in_full() -> None:
    """The index is for choosing what to read; this is the reading."""
    printed = render_thread(DISCUSSED)

    assert printed.startswith("comment-4  `src/routes.py`:118-130  question")
    assert "And if it does, what then?" in printed
    assert "you: It cannot: one queue." in printed
    assert "lines:     return event" in printed


def test_a_review_nobody_answers_says_so() -> None:
    """Because it changes what the agent should do next, or whether it can."""
    printed = render_context(SEEN.model_copy(update={"answerer_attached": False}))

    assert "nobody answering" in printed


def test_an_image_said_in_the_panel_is_listed_as_a_file_to_open() -> None:
    """The words alone would leave "look at this" pointing at nothing."""
    image = Path("/tmp/tmp0a1b.claude-review/images/0a1b.png")
    said = ASKED_TO_RUN_THE_TESTS.model_copy(update={"body": "", "images": [image]})

    printed = render_context(SEEN.model_copy(update={"panel": [said]}))

    assert "reader: (image)" in printed
    assert f"image: {image}" in printed

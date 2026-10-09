"""What the review's shared state promises on its own.

When a review counts as closed, rather than reloaded or not yet opened.
Only the running process acts on this, by ending — which test_cli_process
watches. What can be said without waiting out the grace period in real time
is said here, against the clock the state is handed.

And that a push says what was true when it was pushed, to every review open.
"""

import json

import pytest

from claude_review.hosting.serving import DISCONNECT_GRACE
from claude_review.presentation.schemas import AgentWork
from claude_review.presentation.state import ServerState
from claude_review.services.review_lifetime import ReviewLifetime

# Moments on the review's clock: a socket opened, one more a moment later,
# one dropped a moment after that, and the time before and after the grace
# period has run out on it
OPENED_AT = 100.0
# Short enough that several fit inside the grace period
MOMENTS_PER_GRACE = 10
MOMENT = DISCONNECT_GRACE / MOMENTS_PER_GRACE
SECOND_OPENED_AT = OPENED_AT + MOMENT
DROPPED_AT = SECOND_OPENED_AT + MOMENT
WITHIN_GRACE = DROPPED_AT + MOMENT
PAST_GRACE = DROPPED_AT + DISCONNECT_GRACE + MOMENT

# What the agent says it is doing, and what it goes on to do next
READING = "reading the handler"
REWRITING = "rewriting the handler"
REPORTED_AT = 1


@pytest.fixture
def state() -> ServerState:
    return ServerState(ReviewLifetime())


def test_a_reload_is_not_the_reader_leaving(state: ServerState) -> None:
    """A reload drops the socket and takes it again within a moment."""
    state.connected(now=OPENED_AT)
    state.disconnected(now=DROPPED_AT)

    assert not state.browser_gone(now=WITHIN_GRACE, grace=DISCONNECT_GRACE)
    assert state.browser_gone(now=PAST_GRACE, grace=DISCONNECT_GRACE)


def test_a_server_nobody_has_opened_yet_keeps_waiting(state: ServerState) -> None:
    """Starting without a browser is normal; it is not an abandoned review."""
    assert not state.browser_gone(now=PAST_GRACE, grace=DISCONNECT_GRACE)


def test_a_second_tab_keeps_the_review_alive(state: ServerState) -> None:
    state.connected(now=OPENED_AT)
    state.connected(now=SECOND_OPENED_AT)
    state.disconnected(now=DROPPED_AT)

    assert not state.browser_gone(now=PAST_GRACE, grace=DISCONNECT_GRACE)


def test_a_push_says_what_was_true_when_it_was_pushed(state: ServerState) -> None:
    """Every review open is told the same, and nothing changed afterwards reaches one still to be sent it."""
    first_tab = state.listen()
    second_tab = state.listen()
    work = AgentWork(message_id=None, text=READING, files=[], steps=[], at=REPORTED_AT)

    state.report_work(work)
    work.text = REWRITING

    told = [json.loads(tab.get_nowait()) for tab in (first_tab, second_tab)]
    assert [said["work"]["text"] for said in told] == [READING, READING]

"""When a review counts as closed, rather than reloaded or not yet opened.

Only the running process acts on this, by ending — which test_cli_process
watches. What can be said without waiting out the grace period in real time
is said here, against the clock the state is handed.
"""

import asyncio

import pytest

from claude_review.cli import DISCONNECT_GRACE
from claude_review.presentation.state import ServerState

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


@pytest.fixture
def state() -> ServerState:
    return ServerState(shutdown_event=asyncio.Event())


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

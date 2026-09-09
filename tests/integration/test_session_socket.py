"""The socket that keeps a review alive.

The browser holds it open while the review is on screen; the server winds
down shortly after the last one closes. A poll could not do this, because a
background tab has its timers throttled to about once a minute.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, LineType, ReviewMode
from claude_review.presentation.app import create_app
from claude_review.presentation.state import ServerState

GRACE = 3.0


@pytest.fixture
def state() -> ServerState:
    return ServerState(shutdown_event=asyncio.Event())


@pytest.fixture
def client(state: ServerState) -> TestClient:
    files = [
        DiffFile(
            path="a.py",
            status=FileStatus.MODIFIED,
            hunks=[
                DiffHunk(
                    header="@@ -1 +1 @@",
                    old_start=1,
                    new_start=1,
                    lines=[DiffLine(type=LineType.CONTEXT, old_no=1, new_no=1, content="x = 1")],
                )
            ],
        )
    ]
    return TestClient(create_app(diff_files=files, state=state, mode=ReviewMode.DIFF))


def test_the_review_is_alive_while_a_browser_holds_the_socket(client: TestClient, state: ServerState) -> None:
    with client.websocket_connect("/api/session"):
        assert not state.browser_gone(now=1000.0, grace=GRACE)


def test_the_review_winds_down_once_the_last_browser_leaves(client: TestClient, state: ServerState) -> None:
    with client.websocket_connect("/api/session"):
        pass

    # The loop clock the server read on disconnect is monotonic and far below
    # this, so any grace period has long since passed
    assert state.browser_gone(now=1e12, grace=GRACE)


def test_a_reload_is_not_the_reader_leaving(state: ServerState) -> None:
    """A reload drops the socket and takes it again within a moment."""
    state.connected(now=100.0)
    state.disconnected(now=100.2)

    assert not state.browser_gone(now=100.4, grace=GRACE)
    assert state.browser_gone(now=110.0, grace=GRACE)


def test_a_server_nobody_has_opened_yet_keeps_waiting(state: ServerState) -> None:
    """Starting without a browser is normal; it is not an abandoned review."""
    assert not state.browser_gone(now=1e9, grace=GRACE)


def test_a_second_tab_keeps_the_review_alive(state: ServerState) -> None:
    state.connected(now=100.0)
    state.connected(now=101.0)
    state.disconnected(now=102.0)

    assert not state.browser_gone(now=200.0, grace=GRACE)


def test_the_server_can_push_to_an_open_review(client: TestClient, state: ServerState) -> None:
    """The socket carries messages the other way too."""
    with client.websocket_connect("/api/session") as websocket:
        state.push({"type": "reload"})

        assert websocket.receive_json() == {"type": "reload"}

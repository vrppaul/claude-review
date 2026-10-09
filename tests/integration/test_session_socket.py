"""The socket a review on screen holds open.

The browser holds it while the review is on screen, and the server winds
down shortly after the last one closes — tested against the real process in
test_cli_process, since only the process ends. Over it the page tells the
server what only the page knows: which round it had got to, and the threads
it holds. The server tells the page what happened since.
"""

from http import HTTPStatus
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from claude_review.domain.models import MAX_QUOTE_LINES, CommentSeverity, TurnAuthor
from claude_review.presentation.wire.pushes import PushKind
from tests.helpers import (
    CATCH_UP_ROUTE,
    FIRST_THREAD_ID,
    PNG,
    REVIEWED_FILE,
    line_on_the_wire,
    next_push,
    open_session,
    open_session_at,
    thread_on_the_wire,
    thread_route,
    until_the_review_holds_threads,
    until_the_review_is_on_round,
)

A_THREAD = thread_on_the_wire(line_on_the_wire(REVIEWED_FILE, 1), "Why one?")

SHOWN = {"type": "show", "file": REVIEWED_FILE}


def test_every_review_on_screen_hears_what_the_server_says(review_page: TestClient) -> None:
    """Two tabs are one reader, and either may be the one they are looking at."""
    with open_session(review_page) as first, open_session(review_page) as second:
        review_page.post("/api/show", json={"file": REVIEWED_FILE})

        assert next_push(first, PushKind.SHOW) == SHOWN
        assert next_push(second, PushKind.SHOW) == SHOWN


def test_a_review_still_open_says_which_round_it_is_on(review_page: TestClient) -> None:
    """A restarted server comes back at round one; the browser knows better."""
    with open_session(review_page) as socket:
        socket.send_json({"round": 4})
        until_the_review_is_on_round(review_page, 4)

    assert review_page.get(CATCH_UP_ROUTE).json()["round"] == 4


def test_the_next_round_after_a_restart_carries_the_number_the_browser_kept(review_page: TestClient) -> None:
    """Numbered from the browser's count, not the restarted server's, and the count moves on."""
    with open_session(review_page) as socket:
        socket.send_json({"round": 4})
        until_the_review_is_on_round(review_page, 4)

        sent = review_page.post("/api/submit", json={"threads": [A_THREAD], "end": False}).json()

        assert sent["markdown"].startswith("## Code Review Comments — round 4")
        assert next_push(socket, PushKind.ROUND) == {"type": "round", "number": 5}


def test_a_browser_opened_fresh_does_not_drag_the_review_back(review_page: TestClient) -> None:
    """One reader starting at round one must not undo the rounds already sent."""
    with open_session(review_page) as reading:
        reading.send_json({"round": 3})
        until_the_review_is_on_round(review_page, 3)

    with open_session(review_page) as fresh:
        fresh.send_json({"round": 1})
        # Taken in the order it was said, so once this lands the round has been heard
        fresh.send_json({"threads": [A_THREAD]})
        until_the_review_holds_threads(review_page, 1)

    assert review_page.get(CATCH_UP_ROUTE).json()["round"] == 3


def test_anything_else_on_the_socket_is_ignored(review_page: TestClient) -> None:
    """The socket is a lifeline first; nonsense on it must not break it."""
    with open_session(review_page) as socket:
        socket.send_text("not json at all")
        socket.send_text('{"round": "later"}')
        socket.send_text('{"round": 2}')
        until_the_review_is_on_round(review_page, 2)

        review_page.post("/api/show", json={"file": REVIEWED_FILE})

        assert next_push(socket, PushKind.SHOW) == SHOWN


def test_threads_the_browser_holds_reach_an_agent_with_their_place_named(review_page: TestClient) -> None:
    """An agent arriving late reads where each thread is the way the review writes it."""
    ranged = thread_on_the_wire(line_on_the_wire(REVIEWED_FILE, 3, 5), "Why these?", thread_id="comment-2")

    with open_session(review_page) as socket:
        socket.send_json({"threads": [A_THREAD, ranged]})
        held = until_the_review_holds_threads(review_page, 2)

    assert [(thread["thread_id"], thread["where"]) for thread in held] == [
        ("comment-1", f"`{REVIEWED_FILE}`:1"),
        ("comment-2", f"`{REVIEWED_FILE}`:3-5"),
    ]


def test_an_image_in_a_thread_no_agent_has_read_can_still_be_taken_off(review_page: TestClient) -> None:
    """Telling the server what the review holds is not handing it to anybody."""
    image_id = review_page.post("/api/images", content=PNG).json()["image_id"]
    pictured = {**A_THREAD, "images": [image_id]}

    with open_session(review_page) as socket:
        # Said in one breath, so once the round has landed the thread has too
        socket.send_json({"round": 2, "threads": [pictured]})
        until_the_review_is_on_round(review_page, 2)

    assert review_page.delete(f"/api/images/{image_id}").status_code == HTTPStatus.NO_CONTENT


def test_an_agent_reading_the_threads_is_handed_their_images(review_page: TestClient) -> None:
    """Read, so handed over: the agent may open it at any time from now on."""
    image_id = review_page.post("/api/images", content=PNG).json()["image_id"]
    pictured = {**A_THREAD, "images": [image_id]}

    with open_session(review_page) as socket:
        socket.send_json({"threads": [pictured]})
        until_the_review_holds_threads(review_page, 1)
    read = review_page.get(thread_route(FIRST_THREAD_ID)).json()

    assert [Path(path).name for path in read["images"]] == [image_id]
    assert review_page.delete(f"/api/images/{image_id}").status_code == 409


def test_an_agent_reading_the_index_is_handed_nothing(review_page: TestClient) -> None:
    """An index is for choosing what to read; the image stays the reader's to take off."""
    image_id = review_page.post("/api/images", content=PNG).json()["image_id"]
    pictured = {**A_THREAD, "images": [image_id]}

    with open_session(review_page) as socket:
        socket.send_json({"threads": [pictured]})
        [listed] = until_the_review_holds_threads(review_page, 1)

    assert "images" not in listed
    assert review_page.delete(f"/api/images/{image_id}").status_code == HTTPStatus.NO_CONTENT


def test_a_thread_the_review_does_not_hold_is_not_found(review_page: TestClient) -> None:
    """An empty answer would read as a thread with nothing in it."""
    response = review_page.get(thread_route("comment-404"))

    assert response.status_code == 404


def test_a_thread_the_server_cannot_read_costs_only_itself(review_page: TestClient) -> None:
    """One thread out of bounds must not take the round and every other thread with it."""
    too_long = thread_on_the_wire(
        {**line_on_the_wire(REVIEWED_FILE, 1), "quote": [""] * (MAX_QUOTE_LINES + 1)},
        "Quotes more than the review keeps",
        thread_id="comment-2",
    )

    with open_session(review_page) as socket:
        socket.send_json({"round": 2, "threads": [A_THREAD, too_long]})
        until_the_review_is_on_round(review_page, 2)

    assert [held["thread_id"] for held in until_the_review_holds_threads(review_page, 1)] == ["comment-1"]


def test_a_thread_the_server_cannot_read_still_keeps_its_id_from_being_handed_out(review_page: TestClient) -> None:
    """The browser still holds it: a second thread under the same id would edit and delete as one."""
    unreadable = thread_on_the_wire(
        {**line_on_the_wire(REVIEWED_FILE, 1), "quote": [""] * (MAX_QUOTE_LINES + 1)},
        "Raised before the restart",
        thread_id="raised-7",
        raised_by=TurnAuthor.AUTHOR,
    )
    with open_session(review_page) as socket:
        socket.send_json({"round": 2, "threads": [unreadable]})
        until_the_review_is_on_round(review_page, 2)

    raised = review_page.post(
        "/api/point",
        json={"anchor": line_on_the_wire(REVIEWED_FILE, 1), "body": "And", "severity": CommentSeverity.NOTE},
    )

    assert raised.json()["thread_id"] == "raised-8"


def test_threads_the_reader_deleted_are_forgotten(review_page: TestClient) -> None:
    """Deleting the last thread leaves nothing to tell an agent about, and that is what it is told."""
    with open_session(review_page) as socket:
        socket.send_json({"threads": [A_THREAD]})
        until_the_review_holds_threads(review_page, 1)

        socket.send_json({"threads": []})

        assert until_the_review_holds_threads(review_page, 0) == []


def test_a_restarted_server_does_not_hand_out_an_id_a_thread_already_has(review_page: TestClient) -> None:
    """The browser still holds the agent's threads from before the restart."""
    raised_before = thread_on_the_wire(
        line_on_the_wire(REVIEWED_FILE, 1), "Kept it on purpose", thread_id="raised-3", raised_by=TurnAuthor.AUTHOR
    )
    with open_session(review_page) as socket:
        socket.send_json({"threads": [raised_before]})
        until_the_review_holds_threads(review_page, 1)

    raised = review_page.post(
        "/api/point",
        json={"anchor": line_on_the_wire(REVIEWED_FILE, 1), "body": "And", "severity": CommentSeverity.NOTE},
    )

    assert raised.json()["thread_id"] == "raised-4"


def test_a_binary_frame_is_ignored_and_the_socket_goes_on(review_page: TestClient) -> None:
    """Nothing the page sends is binary; one that arrives anyway must not drop the review."""
    with open_session(review_page) as socket:
        socket.send_bytes(b"\x00\x01")
        socket.send_json({"round": 2})
        until_the_review_is_on_round(review_page, 2)

        review_page.post("/api/show", json={"file": REVIEWED_FILE})

        assert next_push(socket, PushKind.SHOW) == SHOWN


def test_a_socket_to_no_route_is_closed_rather_than_failing(review_page: TestClient) -> None:
    """The page's files answer every other path; a socket there is turned away, not a fault of the server."""
    with pytest.raises(WebSocketDisconnect), open_session_at(review_page, "/api/nowhere") as socket:
        socket.receive_text()

"""The socket a review on screen holds open.

The browser holds it while the review is on screen, and the server winds
down shortly after the last one closes — tested against the real process in
test_cli_process, since only the process ends. Over it the page tells the
server what only the page knows: which round it had got to, and the threads
it holds. The server tells the page what happened since.
"""

from fastapi.testclient import TestClient

from tests.helpers import (
    CONTEXT_ROUTE,
    REVIEWED_FILE,
    next_push,
    open_session,
    until_the_review_holds_threads,
    until_the_review_is_on_round,
)

A_COMMENT = {
    "anchor": {"file": REVIEWED_FILE, "side": "new", "start_line": 1, "end_line": 1},
    "severity": "note",
    "body": "Still reads oddly.",
}

ON_THE_LINE = {"kind": "line", "file": REVIEWED_FILE, "side": "new", "start_line": 1, "end_line": 1}
A_THREAD = {"thread_id": "comment-1", "anchor": ON_THE_LINE, "body": "Why one?"}

SHOWN = {"type": "show", "file": REVIEWED_FILE}


def test_every_review_on_screen_hears_what_the_server_says(review_page: TestClient) -> None:
    """Two tabs are one reader, and either may be the one they are looking at."""
    with open_session(review_page) as first, open_session(review_page) as second:
        review_page.post("/api/show", json={"file": REVIEWED_FILE})

        assert next_push(first, "show") == SHOWN
        assert next_push(second, "show") == SHOWN


def test_a_review_still_open_says_which_round_it_is_on(review_page: TestClient) -> None:
    """A restarted server comes back at round one; the browser knows better."""
    with open_session(review_page) as socket:
        socket.send_json({"round": 4})
        until_the_review_is_on_round(review_page, 4)

    assert review_page.get(CONTEXT_ROUTE).json()["round"] == 4


def test_the_next_round_after_a_restart_carries_the_number_the_browser_kept(review_page: TestClient) -> None:
    """Numbered from the browser's count, not the restarted server's, and the count moves on."""
    with open_session(review_page) as socket:
        socket.send_json({"round": 4})
        until_the_review_is_on_round(review_page, 4)

        sent = review_page.post("/api/submit", json={"comments": [A_COMMENT], "end": False}).json()

        assert sent["markdown"].startswith("## Code Review Comments — round 4")
        assert next_push(socket, "round") == {"type": "round", "number": 5}


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

    assert review_page.get(CONTEXT_ROUTE).json()["round"] == 3


def test_anything_else_on_the_socket_is_ignored(review_page: TestClient) -> None:
    """The socket is a lifeline first; nonsense on it must not break it."""
    with open_session(review_page) as socket:
        socket.send_text("not json at all")
        socket.send_text('{"round": "later"}')
        socket.send_text('{"round": 2}')
        until_the_review_is_on_round(review_page, 2)

        review_page.post("/api/show", json={"file": REVIEWED_FILE})

        assert next_push(socket, "show") == SHOWN


def test_threads_the_browser_holds_reach_an_agent_with_their_place_named(review_page: TestClient) -> None:
    """An agent arriving late reads where each thread is the way the review writes it."""
    ranged = {**A_THREAD, "thread_id": "comment-2", "anchor": {**ON_THE_LINE, "start_line": 3, "end_line": 5}}

    with open_session(review_page) as socket:
        socket.send_json({"threads": [A_THREAD, ranged]})
        held = until_the_review_holds_threads(review_page, 2)

    assert [(thread["thread_id"], thread["where"]) for thread in held] == [
        ("comment-1", f"`{REVIEWED_FILE}`:1"),
        ("comment-2", f"`{REVIEWED_FILE}`:3-5"),
    ]


def test_threads_the_reader_deleted_are_forgotten(review_page: TestClient) -> None:
    """Deleting the last thread leaves nothing to tell an agent about, and that is what it is told."""
    with open_session(review_page) as socket:
        socket.send_json({"threads": [A_THREAD]})
        until_the_review_holds_threads(review_page, 1)

        socket.send_json({"threads": []})

        assert until_the_review_holds_threads(review_page, 0) == []


def test_a_restarted_server_does_not_hand_out_an_id_a_thread_already_has(review_page: TestClient) -> None:
    """The browser still holds the agent's threads from before the restart."""
    raised_before = {**A_THREAD, "thread_id": "raised-3", "body": "Kept it on purpose", "raised_by": "author"}
    with open_session(review_page) as socket:
        socket.send_json({"threads": [raised_before]})
        until_the_review_holds_threads(review_page, 1)

    raised = review_page.post("/api/point", json={"file": REVIEWED_FILE, "start_line": 1, "end_line": 1, "body": "And"})

    assert raised.json()["thread_id"] == "raised-4"

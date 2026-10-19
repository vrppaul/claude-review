"""The socket a review on screen holds open.

The browser holds it while the review is on screen, and the server winds
down shortly after the last one closes — tested against the real process in
test_cli_process, since only the process ends. Over it the page tells the
server what only the page knows: which round it had got to, and the threads
it holds. The server tells the page what happened since.
"""

from http import HTTPStatus
from pathlib import Path
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from claude_review.domain.models import MAX_ID_LENGTH, MAX_QUOTE_LINES, CommentSeverity, TurnAuthor
from claude_review.presentation.wire.pushes import EndedPush, ReplyPush, RoundPush, ShowPush
from claude_review.presentation.wire.session import Welcome
from tests.helpers import (
    CATCH_UP_ROUTE,
    FIRST_THREAD_ID,
    PNG,
    REVIEWED_FILE,
    REVIEWED_LINE,
    SESSION_ROUTE,
    line_on_the_wire,
    next_push,
    open_session,
    open_session_at,
    review_facts,
    thread_on_the_wire,
    thread_route,
    turn_on_the_wire,
    until_the_review_holds_threads,
    until_the_review_is_on_round,
    welcome_of,
)

A_THREAD = thread_on_the_wire(line_on_the_wire(REVIEWED_FILE, 1), "Why one?")

SHOWN = ShowPush(file=REVIEWED_FILE)
ANSWER = "It moved to config"
# A run of the review other than the one serving
ANOTHER_RUN = "another-run"
# A review other than the one serving, that ran on its port before
ANOTHER_REVIEW = "another-review"
# The round a page had reached before its server restarted
ROUND_THE_PAGE_KEPT = 4


def _coming_back(welcome: Welcome) -> str:
    """Where a page coming back connects: naming the review and the run it read, and the last push it was handed."""
    named = {"identity": welcome.identity, "instance": welcome.instance, "after": welcome.sequence}
    return f"{SESSION_ROUTE}?{urlencode(named)}"


def test_a_page_coming_back_is_handed_what_was_said_while_it_was_away(review_page: TestClient) -> None:
    """A laptop asleep drops the socket; the answer given meanwhile must still reach the page."""
    with open_session(review_page) as away:
        last_seen = welcome_of(away)
        away.send_json({"threads": [thread_on_the_wire(line_on_the_wire(REVIEWED_FILE, 1), "Why?")]})
        until_the_review_holds_threads(review_page, 1)
    review_page.post("/api/reply", json={"thread_id": FIRST_THREAD_ID, "body": ANSWER})

    with open_session_at(review_page, _coming_back(last_seen)) as back:
        assert welcome_of(back).resumed
        assert next_push(back, ReplyPush) == ReplyPush(thread_id=FIRST_THREAD_ID, question_id=None, body=ANSWER)


def test_the_facts_say_how_far_the_telling_had_got_when_they_were_read(review_page: TestClient) -> None:
    """A page continues on its socket from where its facts left off, so nothing told in between is missed."""
    review_page.post("/api/show", json={"file": REVIEWED_FILE})

    facts = review_facts(review_page)
    with open_session(review_page) as socket:
        welcome = welcome_of(socket)

    assert (facts.instance, facts.sequence) == (welcome.instance, welcome.sequence)


@pytest.mark.parametrize(
    "named",
    [
        {"instance": "r" * (MAX_ID_LENGTH + 1), "after": 0},
        {"instance": ANOTHER_RUN, "after": -1},
        {"identity": "r" * (MAX_ID_LENGTH + 1), "instance": ANOTHER_RUN, "after": 0},
    ],
    ids=["run-name-too-long", "push-number-below-zero", "review-name-too-long"],
)
def test_a_page_naming_a_place_no_telling_has_is_turned_away(review_page: TestClient, named: dict[str, object]) -> None:
    """Held to the bounds the socket's document gives what a page names in its address."""
    with (
        pytest.raises(WebSocketDisconnect),
        open_session_at(review_page, f"{SESSION_ROUTE}?{urlencode(named)}") as socket,
    ):
        socket.receive_text()


def test_a_page_left_open_on_another_review_is_told_whose_review_answers_and_let_go(review_page: TestClient) -> None:
    """A review over and gone leaves its tab knocking on the port: it is neither told nor heard by the next one."""
    with open_session(review_page) as first:
        serving = welcome_of(first)

    left_on = serving.model_copy(update={"identity": ANOTHER_REVIEW})
    with open_session_at(review_page, _coming_back(left_on)) as socket:
        assert welcome_of(socket).identity == serving.identity
        review_page.post("/api/show", json={"file": REVIEWED_FILE})
        with pytest.raises(WebSocketDisconnect):
            socket.receive_text()


def test_a_page_is_welcomed_by_the_name_of_the_review_it_reached(review_page: TestClient) -> None:
    """Another review may answer on the same port: the page must know it is not its own before saying anything."""
    with open_session(review_page) as socket:
        welcome = welcome_of(socket)

    assert welcome.identity == review_facts(review_page).identity


def test_every_page_open_hears_that_the_review_is_over_once_it_is_sent_for_good(review_page: TestClient) -> None:
    """A tab left open on a review that ended would otherwise try to reach it again, for ever."""
    with open_session(review_page) as first, open_session(review_page) as second:
        review_page.post("/api/submit", json={"threads": [], "body": "Fine", "end": True})

        assert next_push(first, EndedPush) == EndedPush(finished=True)
        assert next_push(second, EndedPush) == EndedPush(finished=True)


def test_a_review_still_open_says_which_round_it_is_on(review_page: TestClient) -> None:
    """A restarted server comes back at round one; the browser knows better."""
    with open_session(review_page) as socket:
        socket.send_json({"round": ROUND_THE_PAGE_KEPT})
        until_the_review_is_on_round(review_page, ROUND_THE_PAGE_KEPT)

    assert review_page.get(CATCH_UP_ROUTE).json()["round"] == ROUND_THE_PAGE_KEPT


def test_the_next_round_after_a_restart_carries_the_number_the_browser_kept(review_page: TestClient) -> None:
    """Numbered from the browser's count, not the restarted server's, and the count moves on."""
    with open_session(review_page) as socket:
        socket.send_json({"round": ROUND_THE_PAGE_KEPT})
        until_the_review_is_on_round(review_page, ROUND_THE_PAGE_KEPT)

        sent = review_page.post("/api/submit", json={"threads": [A_THREAD], "end": False}).json()

        assert sent["markdown"].startswith(f"## Code Review Comments — round {ROUND_THE_PAGE_KEPT}")
        assert next_push(socket, RoundPush) == RoundPush(number=ROUND_THE_PAGE_KEPT + 1)


def test_a_browser_opened_fresh_does_not_drag_the_review_back(review_page: TestClient) -> None:
    """One reader starting at round one must not undo the rounds already sent."""
    with open_session(review_page) as reading:
        reading.send_json({"round": ROUND_THE_PAGE_KEPT})
        until_the_review_is_on_round(review_page, ROUND_THE_PAGE_KEPT)

    with open_session(review_page) as fresh:
        fresh.send_json({"round": 1})
        # Taken in the order it was said, so once this lands the round has been heard
        fresh.send_json({"threads": [A_THREAD]})
        until_the_review_holds_threads(review_page, 1)

    assert review_page.get(CATCH_UP_ROUTE).json()["round"] == ROUND_THE_PAGE_KEPT


def test_anything_else_on_the_socket_is_ignored(review_page: TestClient) -> None:
    """The socket is a lifeline first; nonsense on it must not break it."""
    with open_session(review_page) as socket:
        socket.send_text("not json at all")
        socket.send_text('{"round": "later"}')
        socket.send_text('{"round": 2}')
        until_the_review_is_on_round(review_page, 2)

        review_page.post("/api/show", json={"file": REVIEWED_FILE})

        assert next_push(socket, ShowPush) == SHOWN


def test_threads_the_browser_holds_reach_an_agent_with_their_place_named(review_page: TestClient) -> None:
    """An agent arriving late reads where each thread is the way the review writes it."""
    ranged = thread_on_the_wire(line_on_the_wire(REVIEWED_FILE, 3, 5), "Why these?", thread_id="comment-2")

    with open_session(review_page) as socket:
        socket.send_json({"threads": [A_THREAD, ranged]})
        held = until_the_review_holds_threads(review_page, 2)

    assert [(thread["thread_id"], thread["where"]) for thread in held] == [
        ("comment-1", f"{REVIEWED_FILE}:1"),
        ("comment-2", f"{REVIEWED_FILE}:3-5"),
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
    read = review_page.post(thread_route(FIRST_THREAD_ID)).json()

    assert [Path(path).name for path in read["images"]] == [image_id]
    assert review_page.delete(f"/api/images/{image_id}").status_code == HTTPStatus.CONFLICT


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
    response = review_page.post(thread_route("comment-404"))

    assert response.status_code == HTTPStatus.NOT_FOUND


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


@pytest.mark.parametrize(
    "unreadable_id", ["raised-²", "raised-" + "9" * 5000], ids=["not-an-ascii-digit", "more-digits-than-a-number-takes"]
)
def test_a_thread_whose_id_no_page_gives_costs_only_itself(review_page: TestClient, unreadable_id: str) -> None:
    """The socket is a lifeline first: an id no review hands out must not end it, nor cost the threads beside it."""
    with open_session(review_page) as socket:
        socket.send_json({"round": 2, "threads": [A_THREAD, {"thread_id": unreadable_id}]})
        until_the_review_is_on_round(review_page, 2)

        review_page.post("/api/show", json={"file": REVIEWED_FILE})

        assert next_push(socket, ShowPush) == SHOWN
    assert [held["thread_id"] for held in until_the_review_holds_threads(review_page, 1)] == [FIRST_THREAD_ID]


def test_a_thread_the_server_cannot_read_can_still_be_answered_in(review_page: TestClient) -> None:
    """The browser holds it and draws the answer in it, whatever the server could not make of it."""
    unreadable = thread_on_the_wire(
        {**line_on_the_wire(REVIEWED_FILE, 1), "quote": [""] * (MAX_QUOTE_LINES + 1)}, "Why this?"
    )
    with open_session(review_page) as socket:
        socket.send_json({"round": 2, "threads": [unreadable]})
        until_the_review_is_on_round(review_page, 2)

    answered = review_page.post("/api/reply", json={"thread_id": FIRST_THREAD_ID, "body": "Because"})

    assert answered.status_code == HTTPStatus.NO_CONTENT


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


THREADS_ROUTE = "/api/threads"


def _raised(page: TestClient, body: str) -> str:
    """Raise a thread on the review's one line, as the agent does, and say its id."""
    raised = page.post(
        "/api/point",
        json={"anchor": line_on_the_wire(REVIEWED_FILE, 1), "body": body, "severity": CommentSeverity.NOTE},
    )
    return raised.json()["thread_id"]


def test_a_thread_the_agent_raised_is_held_before_any_page_says_it_holds_it(review_page: TestClient) -> None:
    """A page that opens later, with no draft of its own, learns of it from the review."""
    thread_id = _raised(review_page, "Kept on purpose")

    [held] = review_page.get(THREADS_ROUTE).json()["threads"]

    assert (held["thread_id"], held["body"], held["raised_by"]) == (thread_id, "Kept on purpose", TurnAuthor.AUTHOR)
    assert held["anchor"]["quote"] == [REVIEWED_LINE]


def test_a_thread_the_agent_raised_stays_though_a_page_says_it_holds_none(review_page: TestClient) -> None:
    """A browser with no draft must not take the agent's threads away with it."""
    thread_id = _raised(review_page, "Kept on purpose")

    with open_session(review_page) as socket:
        socket.send_json({"round": 2, "threads": [A_THREAD]})
        until_the_review_is_on_round(review_page, 2)

    held = review_page.get(THREADS_ROUTE).json()["threads"]
    assert sorted(thread["thread_id"] for thread in held) == sorted([FIRST_THREAD_ID, thread_id])
    assert review_page.post(thread_route(thread_id)).status_code == HTTPStatus.OK


def test_a_thread_the_agent_raised_is_held_as_the_page_last_said_it(review_page: TestClient) -> None:
    """The reader's reply in it is what an agent arriving later must read."""
    thread_id = _raised(review_page, "Kept on purpose")
    raised = review_page.get(THREADS_ROUTE).json()["threads"][0]
    replied = {**raised, "turns": [turn_on_the_wire(TurnAuthor.READER, "Why?", turn_id="turn-1")]}

    with open_session(review_page) as socket:
        socket.send_json({"round": 2, "threads": [replied]})
        until_the_review_is_on_round(review_page, 2)

    [held] = review_page.get(THREADS_ROUTE).json()["threads"]
    assert held["thread_id"] == thread_id
    assert [turn["body"] for turn in held["turns"]] == ["Why?"]


def test_a_page_that_says_nothing_of_its_threads_leaves_them_as_the_review_holds_them(
    review_page: TestClient,
) -> None:
    """A page with no draft says nothing of threads until it knows them: it must not wipe them."""
    with open_session(review_page) as socket:
        socket.send_json({"threads": [A_THREAD]})
        until_the_review_holds_threads(review_page, 1)
        socket.send_json({"round": 2, "threads": None})
        until_the_review_is_on_round(review_page, 2)

    assert [held["thread_id"] for held in review_page.get(THREADS_ROUTE).json()["threads"]] == [FIRST_THREAD_ID]


def test_a_binary_frame_is_ignored_and_the_socket_goes_on(review_page: TestClient) -> None:
    """Nothing the page sends is binary; one that arrives anyway must not drop the review."""
    with open_session(review_page) as socket:
        socket.send_bytes(b"\x00\x01")
        socket.send_json({"round": 2})
        until_the_review_is_on_round(review_page, 2)

        review_page.post("/api/show", json={"file": REVIEWED_FILE})

        assert next_push(socket, ShowPush) == SHOWN


def test_a_socket_to_no_route_is_closed_rather_than_failing(review_page: TestClient) -> None:
    """A socket opened where no route takes one is turned away, not a fault of the server."""
    with pytest.raises(WebSocketDisconnect), open_session_at(review_page, "/api/nowhere") as socket:
        socket.receive_text()

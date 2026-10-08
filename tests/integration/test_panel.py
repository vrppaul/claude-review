"""The agent panel: talking about the review, not about one line.

A thread hangs on a line. The panel is for everything else — the plan, the
tests, a file nobody commented on — and it reaches the same agent, over the
same queue, so an answer written after a round arrives after it.
"""

from fastapi.testclient import TestClient
from httpx import AsyncClient

from tests.helpers import (
    CONTEXT_ROUTE,
    DIFF_ROUTE,
    EVENTS_ROUTE,
    REVIEWED_FILE,
    REVIEWED_LINE,
    WAIT_FOR_EVENT,
    next_push,
    open_session,
    until_the_review_holds_threads,
)

MESSAGE = {"message_id": "panel-1", "text": "Run the tests and say what fails."}

THREAD = {
    "anchor": {
        "file": REVIEWED_FILE,
        "side": "new",
        "start_line": 42,
        "end_line": 42,
        "quote": ["    return now - self.started_at > timeout"],
    },
    "thread_id": "comment-1",
    "body": "Why did you drop the None check?",
    "history": [{"author": "reader", "body": "Why did you drop the None check?", "round": 1}],
}

QUESTION = {
    "anchor": {"file": REVIEWED_FILE, "side": "new", "start_line": 42, "end_line": 42, "quote": []},
    "thread_id": "comment-1",
    "question_id": "comment-1",
    "body": "Why did you drop the None check?",
    "severity": "note",
    "resolved": False,
    "raised_by": "reader",
}


async def test_a_message_reaches_whoever_is_waiting(client: AsyncClient) -> None:
    """What is typed in the panel is handed over as its own kind of event."""
    await client.post("/api/message", json=MESSAGE)

    event = (await client.get(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()

    assert event["type"] == "message"
    assert event["message"]["text"] == "Run the tests and say what fails."
    assert event["message"]["message_id"] == "panel-1"


async def test_a_message_carries_the_threads_it_points_at(client: AsyncClient) -> None:
    """A chip is a reference; what travels is the thread it refers to."""
    await client.post("/api/message", json={**MESSAGE, "threads": [THREAD]})

    event = (await client.get(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()

    [thread] = event["message"]["threads"]
    assert thread["thread_id"] == "comment-1"
    assert thread["anchor"]["quote"] == ["    return now - self.started_at > timeout"]
    assert thread["history"][0]["body"] == "Why did you drop the None check?"


async def test_questions_rounds_and_messages_keep_one_order(client: AsyncClient) -> None:
    """One queue, so an answer cannot overtake the round it belongs to."""
    await client.post("/api/ask", json=QUESTION)
    await client.post("/api/submit", json={"comments": [], "end": False})
    await client.post("/api/message", json=MESSAGE)

    handed_in_order = ["question", "round", "message"]

    taken = [(await client.get(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()["type"] for _ in handed_in_order]

    assert taken == handed_in_order


def test_an_answer_lands_in_the_panel_of_a_review_still_open(review_page: TestClient) -> None:
    """The answer comes back down the socket every review already holds."""
    with open_session(review_page) as socket:
        review_page.post("/api/say", json={"message_id": "panel-1", "text": "One failed; fixed and green."})

        assert next_push(socket, "chat") == {
            "type": "chat",
            "message_id": "panel-1",
            "text": "One failed; fixed and green.",
            "files": [],
        }


async def test_stopping_is_a_request_the_agent_picks_up(client: AsyncClient) -> None:
    """Nothing is killed: the withdrawal joins the queue like anything else."""
    await client.post("/api/message", json=MESSAGE)
    await client.post("/api/cancel", json={"message_id": "panel-1"})

    first = (await client.get(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()
    second = (await client.get(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()

    assert first["type"] == "message"
    assert second["type"] == "cancel"
    assert second["cancel"]["message_id"] == "panel-1"


def test_the_author_can_raise_a_thread_on_a_line(review_page: TestClient) -> None:
    """What belongs on the code goes on the code, not into the panel."""
    with open_session(review_page) as socket:
        response = review_page.post(
            "/api/point",
            json={
                "file": REVIEWED_FILE,
                "side": "new",
                "start_line": 1,
                "end_line": 1,
                "body": "I did this differently from what was asked, because...",
                "severity": "question",
            },
        )
        pushed = next_push(socket, "point")

    assert response.json()["thread_id"] == "raised-1"
    assert pushed["thread_id"] == "raised-1"
    assert (pushed["anchor"]["file"], pushed["anchor"]["start_line"]) == (REVIEWED_FILE, 1)
    # Quoted from the diff, so the thread can follow its line when it moves
    assert pushed["anchor"]["quote"] == [REVIEWED_LINE]
    assert pushed["severity"] == "question"


async def test_raised_threads_are_numbered_apart_from_the_readers(client: AsyncClient) -> None:
    """The browser mints its own ids; two sides must not collide."""
    first = await client.post("/api/point", json={"file": REVIEWED_FILE, "start_line": 1, "end_line": 1, "body": "one"})
    second = await client.post(
        "/api/point", json={"file": REVIEWED_FILE, "start_line": 1, "end_line": 1, "body": "two"}
    )

    assert first.json()["thread_id"] == "raised-1"
    assert second.json()["thread_id"] == "raised-2"


async def test_a_backwards_range_is_refused(client: AsyncClient) -> None:
    """A thread that ends before it starts hangs on nothing."""
    response = await client.post(
        "/api/point", json={"file": REVIEWED_FILE, "start_line": 9, "end_line": 2, "body": "nowhere"}
    )

    assert response.status_code == 422


async def test_a_thread_on_a_file_not_under_review_is_refused(client: AsyncClient) -> None:
    """Silently accepting it shows the reader a thread about nothing."""
    response = await client.post(
        "/api/point", json={"file": "src/elsewhere.py", "start_line": 1, "end_line": 1, "body": "here"}
    )

    assert response.status_code == 404
    assert "not in this review" in response.json()["detail"]
    assert REVIEWED_FILE in response.json()["detail"]


async def test_a_thread_on_the_removed_side_must_hang_on_a_removed_line(client: AsyncClient) -> None:
    """An unchanged line has an old number too, but nothing was removed there to talk about."""
    response = await client.post(
        "/api/point",
        json={"file": REVIEWED_FILE, "side": "old", "start_line": 1, "end_line": 1, "body": "this one"},
    )

    assert response.status_code == 422
    assert "does not show removed line 1" in response.json()["detail"]


async def test_a_thread_on_a_line_the_diff_does_not_show_is_refused(client: AsyncClient) -> None:
    """The quote would come back empty and go outdated at the next retake."""
    response = await client.post(
        "/api/point", json={"file": REVIEWED_FILE, "start_line": 900, "end_line": 900, "body": "far away"}
    )

    assert response.status_code == 422
    assert "does not show new line 900" in response.json()["detail"]


async def test_a_thread_on_a_line_the_diff_does_show_is_taken(client: AsyncClient) -> None:
    """The check is a guard, not a hurdle: what is on screen goes through."""
    response = await client.post(
        "/api/point", json={"file": REVIEWED_FILE, "start_line": 1, "end_line": 1, "body": "this line"}
    )

    assert response.status_code == 200


def test_the_agent_may_speak_first(review_page: TestClient) -> None:
    """Work finished while the reader reads is news they should not have to ask for."""
    with open_session(review_page) as socket:
        review_page.post("/api/say", json={"text": "Tests are green again.", "files": ["src/cli.py"]})
        pushed = next_push(socket, "chat")

    assert pushed["message_id"] is None
    assert pushed["files"] == ["src/cli.py"]


def test_what_is_being_done_is_said_while_it_is_done(review_page: TestClient) -> None:
    """Waiting says only that something is happening; this says what."""
    with open_session(review_page) as socket:
        review_page.post(
            "/api/progress",
            json={"message_id": "panel-1", "text": "rewriting the answer handler", "files": ["a.ts", "b.ts"]},
        )
        pushed = next_push(socket, "progress")

    assert pushed["text"] == "rewriting the answer handler"
    assert pushed["files"] == ["a.ts", "b.ts"]


def test_work_that_branched_is_reported_as_branches(review_page: TestClient) -> None:
    """Three subagents are three branches, not a sentence about three subagents."""
    with open_session(review_page) as socket:
        review_page.post(
            "/api/progress",
            json={
                "text": "looking for other callers",
                "steps": [{"text": "ran the tests", "done": True}, {"text": "three subagents out"}],
            },
        )
        pushed = next_push(socket, "progress")

    assert pushed["steps"] == [
        {"text": "ran the tests", "done": True},
        {"text": "three subagents out", "done": False},
    ]


def test_a_file_can_be_brought_into_view_when_asked(review_page: TestClient) -> None:
    """The one thing here that moves the reader's own screen."""
    with open_session(review_page) as socket:
        review_page.post("/api/show", json={"file": REVIEWED_FILE})

        assert next_push(socket, "show") == {"type": "show", "file": REVIEWED_FILE}


def test_the_agent_says_what_only_the_agent_knows(review_page: TestClient) -> None:
    """Model and context cannot be measured here, so they are reported."""
    with open_session(review_page) as socket:
        review_page.post("/api/status", json={"model": "opus-5", "context": "53% of 1M"})
        pushed = next_push(socket, "status")

    assert (pushed["model"], pushed["context"]) == ("opus-5", "53% of 1M")


async def test_a_reloaded_review_learns_the_status_again(client: AsyncClient) -> None:
    """A push is gone once sent; the review has to get it from somewhere."""
    await client.post("/api/status", json={"model": "opus-5", "context": "53% of 1M"})

    diff = (await client.get(DIFF_ROUTE)).json()

    assert diff["agent"]["model"] == "opus-5"
    assert diff["agent"]["context"] == "53% of 1M"
    assert diff["agent"]["at"] is not None


async def test_no_status_is_reported_as_nothing_rather_than_zero(client: AsyncClient) -> None:
    """A number nobody sent is a lie; the panel shows it as unknown."""
    diff = (await client.get(DIFF_ROUTE)).json()

    assert diff["agent"] == {"model": None, "context": None, "at": None}


A_DISCUSSED_THREAD = {
    "anchor": {"file": REVIEWED_FILE, "side": "new", "start_line": 1, "end_line": 1, "quote": [REVIEWED_LINE]},
    "thread_id": "comment-1",
    "body": "Why did you drop the None check?",
    "history": [{"author": "author", "body": "It moved to the caller.", "round": 1}],
    "severity": "question",
}


def test_an_agent_arriving_late_is_told_what_the_review_holds(review_page: TestClient) -> None:
    """`events` hands over what happens next, never what already happened."""
    with open_session(review_page) as socket:
        socket.send_json({"threads": [A_DISCUSSED_THREAD]})
        until_the_review_holds_threads(review_page, 1)
    review_page.post("/api/message", json=MESSAGE)
    review_page.post("/api/say", json={"message_id": "panel-1", "text": "One failed; fixed."})

    seen = review_page.get(CONTEXT_ROUTE).json()

    assert seen["round"] == 1
    assert seen["file_count"] == 1
    assert [thread["thread_id"] for thread in seen["threads"]] == ["comment-1"]
    assert [(entry["author"], entry["text"]) for entry in seen["panel"]] == [
        ("reader", "Run the tests and say what fails."),
        ("author", "One failed; fixed."),
    ]


def test_one_thread_can_be_asked_for_on_its_own(review_page: TestClient) -> None:
    """An index is for choosing what to read; this is the reading."""
    with open_session(review_page) as socket:
        socket.send_json({"threads": [A_DISCUSSED_THREAD, {**A_DISCUSSED_THREAD, "thread_id": "comment-2"}]})
        until_the_review_holds_threads(review_page, 2)

    seen = review_page.get(CONTEXT_ROUTE, params={"thread": "comment-2"}).json()

    assert [thread["thread_id"] for thread in seen["threads"]] == ["comment-2"]
    # Nothing about the panel: it was not what was asked for
    assert seen["panel"] == []

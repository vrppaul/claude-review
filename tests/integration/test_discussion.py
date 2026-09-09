"""Asking about a thread, and the answer coming back.

The reader asks from the browser and carries on writing; the answer arrives
later, pushed into the review that is still on screen. The two halves are
separate processes, which is why a queue sits between them.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from claude_review.domain.models import (
    DiffFile,
    DiffHunk,
    DiffLine,
    FileStatus,
    LineType,
    ReviewMode,
)
from claude_review.presentation.app import create_app
from claude_review.presentation.state import ServerState

LOCAL_ORIGIN = "http://127.0.0.1:8000"
# The test client hardcodes "testserver" as the Host for sockets whatever
# its base URL, so the review's own page has to be stated outright
LOCAL_HEADERS = {"Origin": LOCAL_ORIGIN, "Host": "127.0.0.1:8000"}

QUESTION = {
    "thread_id": "comment-1",
    "question_id": "comment-1",
    "file": "src/a.py",
    "side": "new",
    "start_line": 42,
    "end_line": 42,
    "quote": ["    return now - self.started_at > timeout"],
    "body": "Why did you drop the None check?",
}


@pytest.fixture
def state() -> ServerState:
    return ServerState(shutdown_event=asyncio.Event())


def _files() -> list[DiffFile]:
    return [
        DiffFile(
            path="src/a.py",
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


@pytest.fixture
async def client(state: ServerState):
    app = create_app(diff_files=_files(), state=state, mode=ReviewMode.DIFF)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1:8000") as ac:
        yield ac


async def test_a_question_waits_for_whoever_is_answering(client: AsyncClient, state: ServerState) -> None:
    """Asking does not block the reader; it leaves the question to be taken."""
    response = await client.post("/api/ask", json=QUESTION)

    assert response.status_code == 200
    assert state.events.qsize() == 1


async def test_the_answerer_is_handed_the_question(client: AsyncClient) -> None:
    await client.post("/api/ask", json=QUESTION)

    event = (await client.get("/api/events", params={"wait_seconds": 5})).json()

    assert event["type"] == "question"
    assert event["question"]["thread_id"] == "comment-1"
    assert event["question"]["body"] == "Why did you drop the None check?"
    # The quoted lines travel with it, since the answerer may not have the file
    assert event["question"]["quote"] == ["    return now - self.started_at > timeout"]


async def test_waiting_with_nothing_to_do_says_so(client: AsyncClient) -> None:
    """The caller decides whether to keep waiting, rather than hanging forever."""
    event = (await client.get("/api/events", params={"wait_seconds": 0.2})).json()

    assert event["type"] == "timeout"
    assert event["question"] is None


async def test_questions_are_handed_out_in_the_order_they_were_asked(
    client: AsyncClient,
) -> None:
    await client.post("/api/ask", json={**QUESTION, "thread_id": "first", "body": "one"})
    await client.post("/api/ask", json={**QUESTION, "thread_id": "second", "body": "two"})

    first = (await client.get("/api/events", params={"wait_seconds": 5})).json()
    second = (await client.get("/api/events", params={"wait_seconds": 5})).json()

    assert [first["question"]["thread_id"], second["question"]["thread_id"]] == [
        "first",
        "second",
    ]


async def test_a_question_needs_something_asked(client: AsyncClient) -> None:
    response = await client.post("/api/ask", json={**QUESTION, "body": ""})

    assert response.status_code == 422


async def test_a_question_carries_which_question_it_is(client: AsyncClient) -> None:
    """A thread can have several questions waiting, so an answer needs a name for one."""
    await client.post("/api/ask", json={**QUESTION, "question_id": "turn-2"}, headers=LOCAL_HEADERS)

    event = (await client.get("/api/events?wait_seconds=1", headers=LOCAL_HEADERS)).json()

    assert event["question"]["question_id"] == "turn-2"


def test_an_answer_says_which_question_it_answers(state: ServerState) -> None:
    """Without it the browser files the answer under whatever was asked last."""
    app = create_app(diff_files=_files(), state=state, mode=ReviewMode.DIFF)
    client = TestClient(app, base_url=LOCAL_ORIGIN)

    with client.websocket_connect("/api/session", headers=LOCAL_HEADERS) as socket:
        client.post(
            "/api/reply",
            json={"thread_id": "comment-1", "question_id": "turn-2", "text": "It moved to config"},
        )

        assert socket.receive_json() == {
            "type": "reply",
            "thread_id": "comment-1",
            "question_id": "turn-2",
            "text": "It moved to config",
        }


def test_an_answer_that_names_no_question_still_arrives(state: ServerState) -> None:
    """A person answering by hand should not have to quote an id."""
    app = create_app(diff_files=_files(), state=state, mode=ReviewMode.DIFF)
    client = TestClient(app, base_url=LOCAL_ORIGIN)

    with client.websocket_connect("/api/session", headers=LOCAL_HEADERS) as socket:
        client.post("/api/reply", json={"thread_id": "comment-1", "text": "It moved to config"})

        assert socket.receive_json()["question_id"] is None


def test_an_answer_reaches_the_review_on_screen(state: ServerState) -> None:
    app = create_app(diff_files=_files(), state=state, mode=ReviewMode.DIFF)
    client = TestClient(app, base_url=LOCAL_ORIGIN)

    with client.websocket_connect("/api/session", headers=LOCAL_HEADERS) as socket:
        client.post("/api/reply", json={"thread_id": "comment-1", "text": "Because it moved up"})

        assert socket.receive_json() == {
            "type": "reply",
            "thread_id": "comment-1",
            "question_id": None,
            "text": "Because it moved up",
        }


async def test_the_waiter_is_told_when_the_review_ends(client: AsyncClient, state: ServerState) -> None:
    """Otherwise the answering loop spins until the server process dies."""

    async def end_the_review() -> None:
        await asyncio.sleep(0.2)
        state.shutdown_event.set()

    ending = asyncio.create_task(end_the_review())
    event = (await client.get("/api/events", params={"wait_seconds": 10})).json()
    await ending

    assert event["type"] == "closed"


async def test_waiting_after_the_review_ended_says_so_at_once(client: AsyncClient, state: ServerState) -> None:
    state.shutdown_event.set()

    event = (await client.get("/api/events", params={"wait_seconds": 10})).json()

    assert event["type"] == "closed"

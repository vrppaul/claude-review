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

QUESTION = {
    "thread_id": "comment-1",
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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_a_question_waits_for_whoever_is_answering(client: AsyncClient, state: ServerState) -> None:
    """Asking does not block the reader; it leaves the question to be taken."""
    response = await client.post("/api/ask", json=QUESTION)

    assert response.status_code == 200
    assert state.questions.qsize() == 1


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


def test_an_answer_reaches_the_review_on_screen(state: ServerState) -> None:
    app = create_app(diff_files=_files(), state=state, mode=ReviewMode.DIFF)
    client = TestClient(app)

    with client.websocket_connect("/api/session") as socket:
        client.post("/api/reply", json={"thread_id": "comment-1", "text": "Because it moved up"})

        assert socket.receive_json() == {
            "type": "reply",
            "thread_id": "comment-1",
            "text": "Because it moved up",
        }

"""The agent panel: talking about the review, not about one line.

A thread hangs on a line. The panel is for everything else — the plan, the
tests, a file nobody commented on — and it reaches the same agent, over the
same queue, so an answer written after a round arrives after it.
"""

import asyncio

import pytest
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

MESSAGE = {"message_id": "panel-1", "text": "Run the tests and say what fails."}

THREAD = {
    "thread_id": "comment-1",
    "file": "src/a.py",
    "side": "new",
    "start_line": 42,
    "end_line": 42,
    "quote": ["    return now - self.started_at > timeout"],
    "body": "Why did you drop the None check?",
    "history": [{"author": "reader", "body": "Why did you drop the None check?", "round": 1}],
}

QUESTION = {
    "thread_id": "comment-1",
    "question_id": "comment-1",
    "file": "src/a.py",
    "side": "new",
    "start_line": 42,
    "end_line": 42,
    "quote": [],
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


async def test_a_message_reaches_whoever_is_waiting(client: AsyncClient) -> None:
    """What is typed in the panel is handed over as its own kind of event."""
    await client.post("/api/message", json=MESSAGE)

    event = (await client.get("/api/events?wait_seconds=1")).json()

    assert event["type"] == "message"
    assert event["message"]["text"] == "Run the tests and say what fails."
    assert event["message"]["message_id"] == "panel-1"


async def test_a_message_carries_the_threads_it_points_at(client: AsyncClient) -> None:
    """A chip is a reference; what travels is the thread it refers to."""
    await client.post("/api/message", json={**MESSAGE, "threads": [THREAD]})

    event = (await client.get("/api/events?wait_seconds=1")).json()

    [thread] = event["message"]["threads"]
    assert thread["thread_id"] == "comment-1"
    assert thread["quote"] == ["    return now - self.started_at > timeout"]
    assert thread["history"][0]["body"] == "Why did you drop the None check?"


async def test_questions_rounds_and_messages_keep_one_order(client: AsyncClient) -> None:
    """One queue, so an answer cannot overtake the round it belongs to."""
    await client.post("/api/ask", json=QUESTION)
    await client.post("/api/submit", json={"comments": [], "end": False})
    await client.post("/api/message", json=MESSAGE)

    kinds = [(await client.get("/api/events?wait_seconds=1")).json()["type"] for _ in range(3)]

    assert kinds == ["question", "round", "message"]


async def test_an_answer_lands_in_the_panel_of_a_review_still_open(client: AsyncClient, state: ServerState) -> None:
    """The answer comes back down the socket every review already holds."""
    heard: list[dict] = []
    listener = state.listen()

    await client.post("/api/say", json={"message_id": "panel-1", "text": "One failed; fixed and green."})

    while not listener.empty():
        heard.append(listener.get_nowait())

    assert heard == [{"type": "chat", "message_id": "panel-1", "text": "One failed; fixed and green."}]


async def test_stopping_is_a_request_the_agent_picks_up(client: AsyncClient) -> None:
    """Nothing is killed: the withdrawal joins the queue like anything else."""
    await client.post("/api/message", json=MESSAGE)
    await client.post("/api/cancel", json={"message_id": "panel-1"})

    first = (await client.get("/api/events?wait_seconds=1")).json()
    second = (await client.get("/api/events?wait_seconds=1")).json()

    assert first["type"] == "message"
    assert second["type"] == "cancel"
    assert second["cancel"]["message_id"] == "panel-1"


async def test_the_author_can_raise_a_thread_on_a_line(client: AsyncClient, state: ServerState) -> None:
    """What belongs on the code goes on the code, not into the panel."""
    listener = state.listen()

    response = await client.post(
        "/api/point",
        json={
            "file": "src/a.py",
            "side": "new",
            "start_line": 42,
            "end_line": 44,
            "body": "I did this differently from what was asked, because...",
            "severity": "question",
        },
    )

    assert response.json()["thread_id"] == "raised-1"
    pushed = listener.get_nowait()
    assert pushed["type"] == "point"
    assert pushed["file"] == "src/a.py"
    assert pushed["start_line"] == 42
    assert pushed["severity"] == "question"


async def test_raised_threads_are_numbered_apart_from_the_readers(client: AsyncClient) -> None:
    """The browser mints its own ids; two sides must not collide."""
    first = await client.post("/api/point", json={"file": "a.py", "start_line": 1, "end_line": 1, "body": "one"})
    second = await client.post("/api/point", json={"file": "a.py", "start_line": 2, "end_line": 2, "body": "two"})

    assert first.json()["thread_id"] == "raised-1"
    assert second.json()["thread_id"] == "raised-2"


async def test_a_backwards_range_is_refused(client: AsyncClient) -> None:
    """A thread that ends before it starts hangs on nothing."""
    response = await client.post("/api/point", json={"file": "a.py", "start_line": 9, "end_line": 2, "body": "nowhere"})

    assert response.status_code == 422


async def test_the_agent_says_what_only_the_agent_knows(client: AsyncClient, state: ServerState) -> None:
    """Model and context cannot be measured here, so they are reported."""
    listener = state.listen()

    await client.post("/api/status", json={"model": "opus-5", "context": "53% of 1M"})

    pushed = listener.get_nowait()
    assert pushed["type"] == "status"
    assert pushed["model"] == "opus-5"
    assert pushed["context"] == "53% of 1M"


async def test_a_reloaded_review_learns_the_status_again(client: AsyncClient) -> None:
    """A push is gone once sent; the review has to get it from somewhere."""
    await client.post("/api/status", json={"model": "opus-5", "context": "53% of 1M"})

    diff = (await client.get("/api/diff")).json()

    assert diff["agent"]["model"] == "opus-5"
    assert diff["agent"]["context"] == "53% of 1M"
    assert diff["agent"]["at"] is not None


async def test_no_status_is_reported_as_nothing_rather_than_zero(client: AsyncClient) -> None:
    """A number nobody sent is a lie; the panel shows it as unknown."""
    diff = (await client.get("/api/diff")).json()

    assert diff["agent"] == {"model": None, "context": None, "at": None}

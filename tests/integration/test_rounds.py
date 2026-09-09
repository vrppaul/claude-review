"""Sending a round without ending the review.

A review used to end the moment it was sent: the server wound down and the
tab died, so an answer had nowhere to come back to. A round is the same
send, except the review stays open — the agent answers, changes what it
changed, retakes the diff, and reading continues.
"""

import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, LineType, ReviewMode
from claude_review.presentation.app import create_app
from claude_review.presentation.state import ServerState
from tests.helpers import git

LOCAL_ORIGIN = "http://127.0.0.1:8000"
LOCAL_HEADERS = {"Origin": LOCAL_ORIGIN, "Host": "127.0.0.1:8000"}

A_COMMENT = {
    "file": "src/a.py",
    "side": "new",
    "severity": "note",
    "start_line": 1,
    "end_line": 1,
    "body": "Still reads oddly.",
}


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
def state() -> ServerState:
    return ServerState(shutdown_event=asyncio.Event())


@pytest.fixture
async def client(state: ServerState):
    app = create_app(diff_files=_files(), state=state, mode=ReviewMode.DIFF)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=LOCAL_ORIGIN) as ac:
        yield ac


async def test_a_round_does_not_end_the_review(client: AsyncClient, state: ServerState) -> None:
    response = await client.post("/api/submit", json={"comments": [A_COMMENT], "end": False}, headers=LOCAL_HEADERS)

    assert response.status_code == 200
    assert not state.shutdown_event.is_set()


async def test_sending_without_saying_otherwise_ends_the_review(client: AsyncClient, state: ServerState) -> None:
    """The plain flow is unchanged: one send, and the review is over."""
    response = await client.post("/api/submit", json={"comments": [A_COMMENT]}, headers=LOCAL_HEADERS)

    assert response.status_code == 200
    assert state.shutdown_event.is_set()


async def test_the_answerer_is_handed_the_round(client: AsyncClient) -> None:
    waiting = asyncio.ensure_future(client.get("/api/events?wait_seconds=5", headers=LOCAL_HEADERS))
    await asyncio.sleep(0.05)

    await client.post("/api/submit", json={"comments": [A_COMMENT], "end": False}, headers=LOCAL_HEADERS)
    event = (await waiting).json()

    assert event["type"] == "round"
    assert event["round"]["number"] == 1
    assert "Still reads oddly." in event["round"]["markdown"]


async def test_a_later_round_says_which_round_it_is(client: AsyncClient) -> None:
    await client.post("/api/submit", json={"comments": [A_COMMENT], "end": False}, headers=LOCAL_HEADERS)
    second = await client.post("/api/submit", json={"comments": [A_COMMENT], "end": False}, headers=LOCAL_HEADERS)

    assert second.json()["markdown"].startswith("## Code Review Comments — round 2")


async def test_a_thread_reaches_the_agent_with_what_was_said_in_it(client: AsyncClient) -> None:
    comment = {
        **A_COMMENT,
        "severity": "question",
        "turns": [
            {"author": "author", "body": "Deliberate: two tabs are one reader."},
            {"author": "reader", "body": "Then say so in the docstring."},
        ],
        "resolved": True,
    }

    response = await client.post("/api/submit", json={"comments": [comment]}, headers=LOCAL_HEADERS)
    markdown = response.json()["markdown"]

    assert "> **You:** Deliberate: two tabs are one reader." in markdown
    assert "> **Reviewer:** Then say so in the docstring." in markdown
    assert "question, resolved" in markdown


async def test_ending_the_review_closes_it(client: AsyncClient, state: ServerState) -> None:
    response = await client.post("/api/end", json={}, headers=LOCAL_HEADERS)

    assert response.status_code == 200
    assert state.shutdown_event.is_set()


async def test_a_waiting_agent_is_told_the_review_ended(client: AsyncClient) -> None:
    waiting = asyncio.ensure_future(client.get("/api/events?wait_seconds=5", headers=LOCAL_HEADERS))
    await asyncio.sleep(0.05)

    await client.post("/api/end", json={}, headers=LOCAL_HEADERS)

    assert (await waiting).json()["type"] == "closed"


async def test_retaking_the_diff_serves_what_changed_since(tmp_git_repo: Path, state: ServerState) -> None:
    app = create_app(diff_files=[], state=state, mode=ReviewMode.DIFF, root=tmp_git_repo, base=None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=LOCAL_ORIGIN) as client:
        (tmp_git_repo / "added.py").write_text("print('hi')\n")
        git(tmp_git_repo, "add", ".")

        retaken = await client.post("/api/round", json={}, headers=LOCAL_HEADERS)
        diff = await client.get("/api/diff", headers=LOCAL_HEADERS)

    assert retaken.status_code == 200
    assert retaken.json()["file_count"] == 1
    assert [f["path"] for f in diff.json()["files"]] == ["added.py"]


async def test_a_review_without_a_repository_cannot_retake_its_diff(client: AsyncClient) -> None:
    response = await client.post("/api/round", json={}, headers=LOCAL_HEADERS)

    assert response.status_code == 404


async def test_the_review_learns_that_someone_is_there_to_answer(client: AsyncClient, state: ServerState) -> None:
    """Rounds are only offered when an agent is actually waiting on them."""
    assert not state.answerer_attached

    await client.get("/api/events?wait_seconds=0.1", headers=LOCAL_HEADERS)

    assert state.answerer_attached

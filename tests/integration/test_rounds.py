"""Sending a round without ending the review.

A review used to end the moment it was sent: the server wound down and the
tab died, so an answer had nowhere to come back to. A round is the same
send, except the review stays open — the agent answers, changes what it
changed, retakes the diff, and reading continues.
"""

import asyncio
from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient
from httpx import AsyncClient

from claude_review.domain.models import CommentSeverity, TurnAuthor
from claude_review.presentation.wire.content import ChangesSince
from claude_review.presentation.wire.pushes import AnswererPush, DiffPush
from tests.helpers import (
    DIFF_ROUTE,
    EVENTS_ROUTE,
    GLANCE_AT_EVENTS,
    LOCAL_HEADERS,
    REVIEW_ROUTE,
    REVIEWED_FILE,
    WAIT_FOR_EVENT,
    ReviewFactory,
    git,
    http_client,
    line_on_the_wire,
    next_push,
    open_session,
    page_client,
    review_has_ended,
    thread_on_the_wire,
    turn_on_the_wire,
    until_an_agent_waits,
)

A_THREAD = thread_on_the_wire(line_on_the_wire(REVIEWED_FILE, 1), "Still reads oddly.")


async def test_a_round_does_not_end_the_review(client: AsyncClient) -> None:
    response = await client.post("/api/submit", json={"threads": [A_THREAD], "end": False}, headers=LOCAL_HEADERS)

    assert response.json()["ended"] is False
    assert not await review_has_ended(client)


async def test_the_last_send_ends_the_review(client: AsyncClient) -> None:
    """The plain flow: one send, and the review is over."""
    response = await client.post("/api/submit", json={"threads": [A_THREAD], "end": True}, headers=LOCAL_HEADERS)

    assert response.json()["ended"] is True
    assert await review_has_ended(client)


async def test_a_send_has_to_say_whether_it_is_the_last(client: AsyncClient) -> None:
    """Guessed, it would end a review the reader meant to keep, or keep one they meant to end."""
    response = await client.post("/api/submit", json={"threads": [A_THREAD]}, headers=LOCAL_HEADERS)

    assert response.status_code == 422
    assert not await review_has_ended(client)


async def test_the_answerer_is_handed_the_round(client: AsyncClient) -> None:
    waiting = asyncio.ensure_future(client.get(EVENTS_ROUTE, params=WAIT_FOR_EVENT, headers=LOCAL_HEADERS))
    await until_an_agent_waits(client, LOCAL_HEADERS)

    await client.post("/api/submit", json={"threads": [A_THREAD], "end": False}, headers=LOCAL_HEADERS)
    event = (await waiting).json()

    assert event["type"] == "round"
    assert event["round"]["number"] == 1
    assert "Still reads oddly." in event["round"]["markdown"]


async def test_a_later_round_says_which_round_it_is(client: AsyncClient) -> None:
    await client.post("/api/submit", json={"threads": [A_THREAD], "end": False}, headers=LOCAL_HEADERS)
    second = await client.post("/api/submit", json={"threads": [A_THREAD], "end": False}, headers=LOCAL_HEADERS)

    assert second.json()["markdown"].startswith("## Code Review Comments — round 2")


async def test_a_thread_reaches_the_agent_with_what_was_said_in_it(client: AsyncClient) -> None:
    discussed = thread_on_the_wire(
        line_on_the_wire(REVIEWED_FILE, 1),
        "Still reads oddly.",
        severity=CommentSeverity.QUESTION,
        turns=[
            turn_on_the_wire(TurnAuthor.AUTHOR, "Deliberate: two tabs are one reader.", turn_id="turn-1"),
            turn_on_the_wire(TurnAuthor.READER, "Then say so in the docstring.", turn_id="turn-2"),
        ],
        resolved=True,
    )

    response = await client.post("/api/submit", json={"threads": [discussed], "end": True}, headers=LOCAL_HEADERS)
    markdown = response.json()["markdown"]

    assert "> **You:** Deliberate: two tabs are one reader." in markdown
    assert "> **Reviewer:** Then say so in the docstring." in markdown
    assert "question, resolved" in markdown


async def test_ending_the_review_closes_it(client: AsyncClient) -> None:
    response = await client.post("/api/end", json={}, headers=LOCAL_HEADERS)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert await review_has_ended(client)


async def test_a_waiting_agent_is_told_the_review_ended(client: AsyncClient) -> None:
    waiting = asyncio.ensure_future(client.get(EVENTS_ROUTE, params=WAIT_FOR_EVENT, headers=LOCAL_HEADERS))
    await until_an_agent_waits(client, LOCAL_HEADERS)

    await client.post("/api/end", json={}, headers=LOCAL_HEADERS)

    assert (await waiting).json()["type"] == "closed"


async def test_retaking_the_diff_serves_what_changed_since(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    async with http_client(reviews.app([], root=tmp_git_repo)) as client:
        (tmp_git_repo / "added.py").write_text("print('hi')\n")
        git(tmp_git_repo, "add", ".")

        retaken = await client.post("/api/retake", json={}, headers=LOCAL_HEADERS)
        diff = await client.get(DIFF_ROUTE, headers=LOCAL_HEADERS)

    assert retaken.status_code == 200
    assert retaken.json()["file_count"] == 1
    assert [served["path"] for served in diff.json()["files"]] == ["added.py"]


async def test_a_review_without_a_repository_cannot_retake_its_diff(client: AsyncClient) -> None:
    response = await client.post("/api/retake", json={}, headers=LOCAL_HEADERS)

    assert response.status_code == 404


def test_the_review_learns_that_someone_is_there_to_answer(review_page: TestClient) -> None:
    """Rounds are only offered when an agent is actually waiting on them."""
    with open_session(review_page) as socket:
        before = review_page.get(REVIEW_ROUTE).json()["answerer_attached"]
        review_page.get(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)

        assert next_push(socket, AnswererPush) == AnswererPush(attached=True)

    assert before is False
    # And a review opened only now learns it too
    assert review_page.get(REVIEW_ROUTE).json()["answerer_attached"] is True


def test_a_retake_names_the_files_that_changed_since_the_last_one(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """A file the agent rewrote must not keep the tick that says it was read."""
    (tmp_git_repo / "answered.py").write_text("as it was\n")
    (tmp_git_repo / "untouched.py").write_text("as it was\n")

    with page_client(reviews.app([], root=tmp_git_repo)) as review_page:
        (tmp_git_repo / "answered.py").write_text("as the round asked\n")

        with open_session(review_page) as socket:
            review_page.post("/api/retake", json={})

            told = next_push(socket, DiffPush)

    assert told.changes == ChangesSince(since_round=1, base_key="round:1", paths=["answered.py"])


def test_a_retake_tells_the_page_how_many_files_the_review_now_holds(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """The review's own count: a page reading a narrower base cannot count the review from its screen."""
    with page_client(reviews.app([], root=tmp_git_repo)) as review_page:
        (tmp_git_repo / "added.py").write_text("print('hi')\n")
        git(tmp_git_repo, "add", ".")

        with open_session(review_page) as socket:
            review_page.post("/api/retake", json={})
            told = next_push(socket, DiffPush)

    assert told.file_count == 1


def test_a_retake_is_measured_from_where_the_round_began(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """Twice through the loop in one round, and the count still means what it says.

    The agent may take the diff again several times while one round is being
    written. Measuring each from the take before it would leave "3 files have
    changed since round 1" opening a screen of five: the base the reader is
    offered for round 1 is where round 1 began, so the count is taken from
    there too.
    """
    (tmp_git_repo / "first.py").write_text("one\n")

    with page_client(reviews.app([], root=tmp_git_repo)) as review_page:
        (tmp_git_repo / "first.py").write_text("two\n")
        review_page.post("/api/retake", json={})

        with open_session(review_page) as socket:
            (tmp_git_repo / "second.py").write_text("only this one now\n")
            review_page.post("/api/retake", json={})
            told = next_push(socket, DiffPush)

    assert told.changes is not None
    assert told.changes.since_round == 1
    assert sorted(told.changes.paths) == ["first.py", "second.py"]


def test_a_review_that_keeps_nothing_says_it_cannot_tell_what_changed(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """Without a mark to compare against, the review must not claim nothing moved."""
    with (
        page_client(reviews.app([], root=tmp_git_repo, keeps_marks=False)) as review_page,
        open_session(review_page) as socket,
    ):
        review_page.post("/api/retake", json={})

        assert next_push(socket, DiffPush).changes is None


async def test_after_a_retake_each_thread_is_told_where_its_lines_went(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """The browser holds the threads and the server holds the diff they hang on."""
    (tmp_git_repo / "a.py").write_text("def run():\n    return 1\n")
    on_run = {"file": "a.py", "side": "new", "start_line": 1, "end_line": 1, "quote": ["def run():"]}
    on_walk = {**on_run, "quote": ["def walk():"]}

    async with http_client(reviews.app([], root=tmp_git_repo)) as client:
        (tmp_git_repo / "a.py").write_text("import sys\ndef run():\n    return 1\n")
        await client.post("/api/retake", json={}, headers=LOCAL_HEADERS)
        response = await client.post("/api/anchors/follow", json={"anchors": [on_run, on_walk]}, headers=LOCAL_HEADERS)

    followed, gone = response.json()["anchors"]
    assert (followed["start_line"], followed["outdated"]) == (2, False)
    assert (gone["start_line"], gone["outdated"]) == (1, True)

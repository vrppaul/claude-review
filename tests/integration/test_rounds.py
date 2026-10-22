"""Sending a round without ending the review.

A review used to end the moment it was sent: the server wound down and the
tab died, so an answer had nowhere to come back to. A round is the same
send, except the review stays open — the agent answers, changes what it
changed, retakes the diff, and reading continues.
"""

import asyncio
from http import HTTPStatus
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from claude_review.presentation.schemas.pushes import AnswererPush, DiffPush, HandedPush
from claude_review.services.review_opening import ReviewOpening
from tests.helpers import (
    DIFF_ROUTE,
    EVENTS_ROUTE,
    FIRST_THREAD_ID,
    GLANCE_AT_EVENTS,
    LOCAL_HEADERS,
    REVIEW_ROUTE,
    REVIEWED_FILE,
    WAIT_FOR_EVENT,
    ReviewFactory,
    git,
    http_client,
    line_json,
    next_push,
    open_session,
    page_client,
    repository_opening,
    review_has_ended,
    thread_json,
    until_an_agent_waits,
)

A_THREAD = thread_json(line_json(REVIEWED_FILE, 1), "Still reads oddly.")


@pytest.fixture
async def opened_repository(tmp_git_repo: Path) -> ReviewOpening:
    """The repository under review, as the command line opens it; the review reads its diff again as it opens."""
    return await repository_opening(tmp_git_repo)


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

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert not await review_has_ended(client)


async def test_the_answerer_is_handed_the_round(client: AsyncClient) -> None:
    waiting = asyncio.ensure_future(client.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT, headers=LOCAL_HEADERS))
    await until_an_agent_waits(client, LOCAL_HEADERS)

    await client.post("/api/submit", json={"threads": [A_THREAD], "end": False}, headers=LOCAL_HEADERS)
    event = (await waiting).json()

    assert event["type"] == "round"
    assert event["round"]["number"] == 1
    assert "Still reads oddly." in event["round"]["markdown"]


def test_every_page_hears_what_a_round_handed_the_agent(review_page: TestClient) -> None:
    """The comment went with the round: it is the agent's to read as it was sent, and the reader's no longer."""
    with open_session(review_page) as socket:
        review_page.post("/api/submit", json={"threads": [A_THREAD], "end": False})

        assert next_push(socket, HandedPush) == HandedPush(thread_id=FIRST_THREAD_ID, said=[FIRST_THREAD_ID])


async def test_a_later_round_says_which_round_it_is(client: AsyncClient) -> None:
    await client.post("/api/submit", json={"threads": [A_THREAD], "end": False}, headers=LOCAL_HEADERS)
    second = await client.post("/api/submit", json={"threads": [A_THREAD], "end": False}, headers=LOCAL_HEADERS)

    assert second.json()["markdown"].startswith("## Code Review Comments — round 2")


async def test_a_thread_quoting_fewer_lines_than_it_names_is_refused(client: AsyncClient) -> None:
    """The page drew only some of those lines: an agent applying the suggestion would delete the rest unseen."""
    across_a_gap = {**line_json(REVIEWED_FILE, 1, 3), "quote": ["the first line, and no other"]}
    thread = thread_json(across_a_gap, "Replace these.")

    response = await client.post("/api/submit", json={"threads": [thread], "end": False}, headers=LOCAL_HEADERS)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert "names 3 lines but quotes 1" in response.json()["detail"]
    assert (await client.get(REVIEW_ROUTE, headers=LOCAL_HEADERS)).json()["round"] == 1


async def test_ending_the_review_closes_it(client: AsyncClient) -> None:
    response = await client.post("/api/end", json={}, headers=LOCAL_HEADERS)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert await review_has_ended(client)


async def test_a_waiting_agent_is_told_the_review_ended(client: AsyncClient) -> None:
    waiting = asyncio.ensure_future(client.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT, headers=LOCAL_HEADERS))
    await until_an_agent_waits(client, LOCAL_HEADERS)

    await client.post("/api/end", json={}, headers=LOCAL_HEADERS)

    assert (await waiting).json()["type"] == "closed"


async def test_retaking_the_diff_serves_what_changed_since(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        (tmp_git_repo / "added.py").write_text("print('hi')\n")
        git(tmp_git_repo, "add", ".")

        retaken = await client.post("/api/retake", json={}, headers=LOCAL_HEADERS)
        diff = await client.get(DIFF_ROUTE, headers=LOCAL_HEADERS)

    assert retaken.status_code == HTTPStatus.OK
    assert retaken.json()["file_count"] == 1
    assert [served["path"] for served in diff.json()["files"]] == ["added.py"]


async def test_a_review_without_a_repository_cannot_retake_its_diff(files_client: AsyncClient) -> None:
    response = await files_client.post("/api/retake", json={}, headers=LOCAL_HEADERS)

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_the_review_learns_that_someone_is_there_to_answer(review_page: TestClient) -> None:
    """Rounds are only offered when an agent is actually waiting on them."""
    with open_session(review_page) as socket:
        before = review_page.get(REVIEW_ROUTE).json()["answerer_attached"]
        review_page.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)

        assert next_push(socket, AnswererPush) == AnswererPush(attached=True)

    assert before is False
    # And a review opened only now learns it too
    assert review_page.get(REVIEW_ROUTE).json()["answerer_attached"] is True


def test_a_retake_tells_the_page_how_many_files_the_review_now_holds(
    tmp_git_repo: Path, reviews: ReviewFactory, opened_repository: ReviewOpening
) -> None:
    """The review's own count: a page reading a narrower base cannot count the review from its screen."""
    with page_client(reviews.app(opened_repository)) as review_page:
        (tmp_git_repo / "added.py").write_text("print('hi')\n")
        git(tmp_git_repo, "add", ".")

        with open_session(review_page) as socket:
            review_page.post("/api/retake", json={})
            told = next_push(socket, DiffPush)

    assert told.file_count == 1


def test_a_retake_is_measured_from_where_the_round_began(
    tmp_git_repo: Path, reviews: ReviewFactory, opened_repository: ReviewOpening
) -> None:
    """Twice through the loop in one round, and the count still means what it says.

    The agent may take the diff again several times while one round is being
    written. Measuring each from the take before it would leave "3 files have
    changed since round 1" opening a screen of five: the base the reader is
    offered for round 1 is where round 1 began, so the count is taken from
    there too.
    """
    (tmp_git_repo / "first.py").write_text("one\n")

    with page_client(reviews.app(opened_repository)) as review_page:
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
    reviews: ReviewFactory, opened_repository: ReviewOpening
) -> None:
    """Without a mark to compare against, the review must not claim nothing moved."""
    with (
        page_client(reviews.app(opened_repository, keeps_marks=False)) as review_page,
        open_session(review_page) as socket,
    ):
        review_page.post("/api/retake", json={})

        assert next_push(socket, DiffPush).changes is None


async def test_after_a_retake_each_thread_is_told_where_its_lines_went(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """The browser holds the threads and the server holds the diff they hang on."""
    (tmp_git_repo / "a.py").write_text("def run():\n    return 1\n")
    on_run = {**line_json("a.py", 1), "quote": ["def run():"]}
    on_walk = {**on_run, "quote": ["def walk():"]}

    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        (tmp_git_repo / "a.py").write_text("import sys\ndef run():\n    return 1\n")
        await client.post("/api/retake", json={}, headers=LOCAL_HEADERS)
        response = await client.post("/api/anchors/follow", json={"anchors": [on_run, on_walk]}, headers=LOCAL_HEADERS)

    followed, gone = response.json()["anchors"]
    assert (followed["start_line"], followed["outdated"]) == (2, False)
    assert (gone["start_line"], gone["outdated"]) == (1, True)

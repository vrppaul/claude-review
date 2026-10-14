"""What an agent waiting on the review is handed, and that nothing handed over is lost on the way.

The agent waits in a loop of separate polls, each a command that may be
killed or time out, and the review may end between two of them. Whatever the
reader handed over is still the agent's to read through all of that.
"""

import asyncio
from http import HTTPMethod, HTTPStatus
from pathlib import Path

import pytest
from httpx import AsyncClient
from pydantic import JsonValue

from tests.helpers import (
    EVENTS_ROUTE,
    FIRST_THREAD_ID,
    GLANCE_AT_EVENTS,
    LOCAL_HEADERS,
    REVIEWED_FILE,
    SETTLE_SECONDS,
    STORY_REQUEST_ROUTE,
    CallerThatLeaves,
    ReviewFactory,
    http_client,
    line_on_the_wire,
    methods_allowed,
    one_line_file,
    opening_of,
    repository_opening,
    thread_on_the_wire,
    thread_route,
    until_an_agent_waits,
    write_files,
)
from tests.stories import ONLY_CHAPTER, as_the_agent_writes, step, story_of

A_THREAD = thread_on_the_wire(line_on_the_wire(REVIEWED_FILE, 1), "Still reads oddly.")
A_MESSAGE = {"message_id": "panel-1", "body": "Is the retry still needed?"}

# Far longer than the test waits for anything, so a poll that is still
# waiting when the test looks is one that never noticed its caller leave
ABANDONED_POLL_SECONDS = SETTLE_SECONDS * 10

STORY_ROUTE = "/api/story"
SUBMIT_ROUTE = "/api/submit"
RETAKE_ROUTE = "/api/retake"
# The file the repository was committed with, as the change leaves it, with two lines gained that a story
# tells; and as a round's work leaves it, those two taken out, and one line put above that no step tells
TOLD_FILE = "initial.txt"
TOLD_CONTENT = "initial content\ntwo\nthree\n"
TAKEN_OUT_UNDER_ONE_MORE = "zero\ninitial content\n"
# And as another round's work leaves it: two lines put above everything, and the first of the two said another way
TWO_ABOVE_AND_TWO_REWORDED = "above\nabove again\ninitial content\nTwo\nthree\n"


async def stale_once_rewritten(reviews: ReviewFactory, repository: Path, rewritten: str) -> JsonValue:
    """What went stale of a story of the two lines gained, as the agent hears it once a round rewrote their file."""
    write_files(repository, {TOLD_FILE: TOLD_CONTENT})
    async with http_client(reviews.app(await repository_opening(repository))) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(story_of(step(TOLD_FILE, 2, 3))))
        await agent.post(SUBMIT_ROUTE, json={"threads": [], "body": "Say it another way.", "end": False})
        # The agent takes the round, does its work, and the diff is taken again
        await agent.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)
        write_files(repository, {TOLD_FILE: rewritten})
        await agent.post(RETAKE_ROUTE)
        await agent.post(STORY_REQUEST_ROUTE)

        return (await agent.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()["stale"]


async def test_a_poll_whose_caller_left_takes_nothing_meant_for_the_next(reviews: ReviewFactory) -> None:
    """A killed `wait` must not leave behind a poll that swallows the next question."""
    app = reviews.app(opening_of([one_line_file()]))
    caller = CallerThatLeaves()
    async with http_client(app) as agent:
        abandoned = asyncio.ensure_future(caller.poll(app, ABANDONED_POLL_SECONDS))
        await until_an_agent_waits(agent)

        caller.gone.set()
        # Over once its caller has gone, rather than waiting out its time
        await asyncio.wait_for(abandoned, timeout=SETTLE_SECONDS)
        await agent.post("/api/message", json=A_MESSAGE)
        event = (await agent.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()

    assert event["type"] == "message"
    assert event["message"]["body"] == A_MESSAGE["body"]


async def test_the_last_round_reaches_an_agent_that_asks_after_the_review_ended(client: AsyncClient) -> None:
    """Sent as the last act, it is the agent's to read before it hears the review is over.

    This holds for as long as the server is up; the process stops a moment
    later and writes out what was never taken (test_cli_process).
    """
    await client.post("/api/submit", json={"threads": [A_THREAD], "end": True}, headers=LOCAL_HEADERS)

    first = (await client.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()
    second = (await client.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()

    assert first["type"] == "round"
    assert "Still reads oddly." in first["round"]["markdown"]
    assert second == {"type": "closed"}


async def test_an_event_carries_only_what_it_is(client: AsyncClient) -> None:
    """A message is not also an empty question, round and cancel."""
    await client.post("/api/message", json=A_MESSAGE)

    event = (await client.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()

    assert set(event) == {"type", "message"}


async def test_nothing_handed_over_says_so_and_nothing_else(client: AsyncClient) -> None:
    """The caller decides whether to keep waiting, rather than hanging forever."""
    event = (await client.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()

    assert event == {"type": "timeout"}


async def test_a_story_asked_for_where_none_was_told_says_nothing_went_stale(
    reviews: ReviewFactory, tmp_git_repo: Path
) -> None:
    write_files(tmp_git_repo, {TOLD_FILE: TOLD_CONTENT})
    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as agent:
        await agent.post(STORY_REQUEST_ROUTE)

        event = (await agent.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()

    assert event == {"type": "story_request", "stale": None}


async def test_a_story_asked_for_again_once_a_round_moved_its_code_on_tells_the_agent_what_went_stale(
    reviews: ReviewFactory, tmp_git_repo: Path
) -> None:
    """Each step whose code changed, by its chapter, its file and its lines as they now stand, or none where its code
    is no longer found, as here, every line of it taken out; and what no step tells."""
    stale = await stale_once_rewritten(reviews, tmp_git_repo, TAKEN_OUT_UNDER_ONE_MORE)

    assert stale == {
        "round": 2,
        "steps": [{"chapter": ONLY_CHAPTER, "file": TOLD_FILE, "lines": None}],
        "left_out": 1,
    }


async def test_a_step_a_round_pushed_down_and_partly_rewrote_is_told_to_the_agent_where_it_now_stands(
    reviews: ReviewFactory, tmp_git_repo: Path
) -> None:
    """Not on the lines it was told of, which now hold other code: on its own, moved down, the line said another way
    at its top still its own, and only the two put above left out."""
    stale = await stale_once_rewritten(reviews, tmp_git_repo, TWO_ABOVE_AND_TWO_REWORDED)

    assert stale == {
        "round": 2,
        "steps": [{"chapter": ONLY_CHAPTER, "file": TOLD_FILE, "lines": "4-5"}],
        "left_out": 2,
    }


@pytest.mark.parametrize("route", [EVENTS_ROUTE, thread_route(FIRST_THREAD_ID)], ids=["an-event", "a-thread"])
async def test_what_hands_something_over_to_the_agent_is_never_a_read(client: AsyncClient, route: str) -> None:
    """A read must change nothing: a link, an image or a prefetch takes nothing meant for the agent."""
    response = await client.get(route)

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert methods_allowed(response) == {HTTPMethod.POST}

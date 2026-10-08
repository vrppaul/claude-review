"""What an agent waiting on the review is handed, and that nothing handed over is lost on the way.

The agent waits in a loop of separate polls, each a command that may be
killed or time out, and the review may end between two of them. Whatever the
reader handed over is still the agent's to read through all of that.
"""

import asyncio

from httpx import AsyncClient

from tests.helpers import (
    EVENTS_ROUTE,
    GLANCE_AT_EVENTS,
    LOCAL_HEADERS,
    REVIEWED_FILE,
    SETTLE_SECONDS,
    CallerThatLeaves,
    ReviewFactory,
    http_client,
    line_on_the_wire,
    one_line_file,
    thread_on_the_wire,
    until_an_agent_waits,
)

A_THREAD = thread_on_the_wire(line_on_the_wire(REVIEWED_FILE, 1), "Still reads oddly.")
A_MESSAGE = {"message_id": "panel-1", "text": "Is the retry still needed?"}

# Far longer than the test waits for anything, so a poll that is still
# waiting when the test looks is one that never noticed its caller leave
ABANDONED_POLL_SECONDS = SETTLE_SECONDS * 10


async def test_a_poll_whose_caller_left_takes_nothing_meant_for_the_next(reviews: ReviewFactory) -> None:
    """A killed `wait` must not leave behind a poll that swallows the next question."""
    app = reviews.app([one_line_file()])
    caller = CallerThatLeaves()
    async with http_client(app) as agent:
        abandoned = asyncio.ensure_future(caller.poll(app, ABANDONED_POLL_SECONDS))
        await until_an_agent_waits(agent)

        caller.gone.set()
        # Over once its caller has gone, rather than waiting out its time
        await asyncio.wait_for(abandoned, timeout=SETTLE_SECONDS)
        await agent.post("/api/message", json=A_MESSAGE)
        event = (await agent.get(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()

    assert event["type"] == "message"
    assert event["message"]["text"] == A_MESSAGE["text"]


async def test_the_last_round_reaches_an_agent_that_asks_after_the_review_ended(client: AsyncClient) -> None:
    """Sent as the last act, it is the agent's to read before it hears the review is over."""
    await client.post("/api/submit", json={"threads": [A_THREAD], "end": True}, headers=LOCAL_HEADERS)

    first = (await client.get(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()
    second = (await client.get(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()

    assert first["type"] == "round"
    assert "Still reads oddly." in first["round"]["markdown"]
    assert second == {"type": "closed"}


async def test_an_event_carries_only_what_it_is(client: AsyncClient) -> None:
    """A message is not also an empty question, round and cancel."""
    await client.post("/api/message", json=A_MESSAGE)

    event = (await client.get(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()

    assert set(event) == {"type", "message"}


async def test_nothing_handed_over_says_so_and_nothing_else(client: AsyncClient) -> None:
    """The caller decides whether to keep waiting, rather than hanging forever."""
    event = (await client.get(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()

    assert event == {"type": "timeout"}

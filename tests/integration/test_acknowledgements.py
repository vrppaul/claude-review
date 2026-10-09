"""What a request that only asks for something to be done is answered: that it was, and nothing more.

The commands the agent runs and the page both read a refusal for what went
wrong; a request that went through has nothing to say, and says nothing
rather than a word nobody reads.
"""

from http import HTTPStatus

import pytest
from httpx import AsyncClient

from tests.helpers import FIRST_THREAD_ID, PNG, REVIEWED_FILE, line_on_the_wire, thread_on_the_wire

A_THREAD = thread_on_the_wire(line_on_the_wire(REVIEWED_FILE, 1), "Why one?")

# Every request that is answered by being done, with a body it takes
DONE_BY_ASKING = [
    ("/api/ask", {"question_id": FIRST_THREAD_ID, "thread": A_THREAD}),
    ("/api/reply", {"thread_id": FIRST_THREAD_ID, "body": "Because"}),
    ("/api/message", {"message_id": "panel-1", "body": "Still there?"}),
    ("/api/say", {"body": "Tests are green."}),
    ("/api/progress", {"text": "reading the handler"}),
    ("/api/show", {"file": REVIEWED_FILE}),
    ("/api/cancel", {"message_id": "panel-1"}),
    ("/api/status", {"model": "opus-5"}),
    ("/api/end", {}),
]


@pytest.mark.parametrize(("route", "body"), DONE_BY_ASKING)
async def test_a_request_that_went_through_says_nothing_more(client: AsyncClient, route: str, body: dict) -> None:
    response = await client.post(route, json=body)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""


async def test_an_image_taken_off_says_nothing_more(client: AsyncClient) -> None:
    image_id = (await client.post("/api/images", content=PNG)).json()["image_id"]

    response = await client.delete(f"/api/images/{image_id}")

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""

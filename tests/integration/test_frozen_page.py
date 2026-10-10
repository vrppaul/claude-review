"""A page that stops reading its socket, against the server a review really runs on.

A laptop put to sleep with the review open keeps its connection and reads
nothing. Whatever the review tells it must back up into that page's own
bounded backlog and get it let go, not pile up in the server's memory.
"""

from http import HTTPStatus

from httpx import AsyncClient
from structlog.typing import EventDict

from claude_review.domain.models import ReviewMode
from claude_review.presentation.broadcast import PAGE_BACKLOG
from claude_review.presentation.wire.base import MAX_TEXT_LENGTH
from tests.helpers import ReviewServers
from tests.page_socket import page_socket_held

# How little the page's side of the connection buffers: it reads nothing, so
# everything else waits on the server's side
PAGE_RECEIVE_BUFFER = 4096
# Enough answers to fill the page's backlog several times over, whatever the
# connection between them holds
ANSWER_COUNT = PAGE_BACKLOG * 4
# Each answer as long as one may be
ANSWER = "x" * MAX_TEXT_LENGTH
REPLY_ROUTE = "/api/reply"
CATCH_UP_ROUTE = "/api/catch-up"


async def test_a_page_that_stops_reading_is_let_go(servers: ReviewServers, logged: list[EventDict]) -> None:
    review = await servers.start([], mode=ReviewMode.FILES)

    # The page reads the handshake's answer and nothing after it
    async with (
        page_socket_held(review.port, receive_buffer=PAGE_RECEIVE_BUFFER),
        AsyncClient(base_url=review.url) as agent,
    ):
        for _ in range(ANSWER_COUNT):
            await agent.post(REPLY_ROUTE, json={"thread_id": "comment-1", "body": ANSWER})
        still_there = await agent.get(CATCH_UP_ROUTE)

    assert "page_fell_behind" in [entry["event"] for entry in logged]
    assert still_there.status_code == HTTPStatus.OK, "a page that stopped reading must not stop the review"

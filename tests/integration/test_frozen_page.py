"""A page that stops reading its socket, against the server a review really runs on.

A laptop put to sleep with the review open keeps its connection and reads
nothing. Whatever the review tells it must back up into that page's own
bounded backlog and get it let go, not pile up in the server's memory; and
the page, once it reads again, must find its socket closed with words that
say "come back later", so it reconnects and is handed what it missed.
"""

import asyncio
import contextlib
from http import HTTPStatus

from httpx import AsyncClient
from structlog.typing import EventDict

from claude_review.domain.models import ReviewMode
from claude_review.presentation.broadcast import PAGE_BACKLOG
from claude_review.presentation.routers.session import FELL_BEHIND
from claude_review.presentation.schemas.base import MAX_TEXT_LENGTH
from tests.helpers import (
    FIRST_THREAD_ID,
    SETTLE_SECONDS,
    ReviewServers,
    line_json,
    opening_of,
    thread_json,
)
from tests.page_socket import PageSocket, page_socket_held

# How little the page's side of the connection buffers: it reads nothing, so
# everything else waits on the server's side
PAGE_RECEIVE_BUFFER = 4096
# Enough answers to fill the page's backlog several times over, whatever the
# connection between them holds
ANSWER_COUNT = PAGE_BACKLOG * 4
# Each answer as long as one may be
ANSWER = "x" * MAX_TEXT_LENGTH
REPLY_ROUTE = "/api/reply"
ASK_ROUTE = "/api/ask"
# The thread the reader asked about before the laptop went to sleep, which every answer is given in
ASKED = {"question_id": FIRST_THREAD_ID, "thread": thread_json(line_json("a.py", 1), "Why?")}
CATCH_UP_ROUTE = "/api/catch-up"


def _read_to_the_end(page: PageSocket) -> int | None:
    """Read whatever the review still sends the page, and say how it closed the socket.

    A socket the review never closes leaves nothing to read, and the read
    that waits on it fails the test.
    """
    with contextlib.suppress(ConnectionError):
        while True:
            page.receive(timeout=SETTLE_SECONDS)
    return page.closed_with


async def test_a_page_that_stops_reading_is_let_go_and_told_to_come_back_later(
    servers: ReviewServers, logged: list[EventDict]
) -> None:
    review = await servers.start(opening_of([], mode=ReviewMode.FILES))

    # The page reads the handshake's answer and nothing after it
    async with (
        page_socket_held(review.port, receive_buffer=PAGE_RECEIVE_BUFFER) as page,
        AsyncClient(base_url=review.url) as agent,
    ):
        await agent.post(ASK_ROUTE, json=ASKED)
        for _ in range(ANSWER_COUNT):
            await agent.post(REPLY_ROUTE, json={"thread_id": FIRST_THREAD_ID, "body": ANSWER})
        still_there = await agent.get(CATCH_UP_ROUTE)
        # The laptop wakes, and the page reads again
        closed_with = await asyncio.to_thread(_read_to_the_end, page)

    assert "page_fell_behind" in [entry["event"] for entry in logged]
    assert still_there.status_code == HTTPStatus.OK, "a page that stopped reading must not stop the review"
    assert closed_with == FELL_BEHIND

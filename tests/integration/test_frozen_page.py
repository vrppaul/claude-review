"""A page that stops reading its socket, against the server a review really runs on.

A laptop put to sleep with the review open keeps its connection and reads
nothing. Whatever the review tells it must back up into that page's own
bounded backlog and get it let go, not pile up in the server's memory.
"""

import asyncio
import base64
import os
import socket

from httpx import AsyncClient
from structlog.typing import EventDict

from claude_review.domain.models import ReviewMode
from claude_review.presentation.broadcast import PAGE_BACKLOG
from claude_review.presentation.wire.base import MAX_TEXT_LENGTH
from tests.helpers import LOOPBACK, SESSION_ROUTE, ReviewServers, RunningReview

# How little the page's side of the connection buffers: it reads nothing, so
# everything else waits on the server's side
PAGE_RECEIVE_BUFFER = 4096
# Enough answers to fill the page's backlog several times over, whatever the
# connection between them holds
ANSWER_COUNT = PAGE_BACKLOG * 4
# Each answer as long as one may be
ANSWER = "x" * MAX_TEXT_LENGTH
# The bytes a websocket handshake key is made of
HANDSHAKE_KEY_BYTES = 16
# How much of the handshake's answer is read before the page stops reading
HANDSHAKE_ANSWER_BYTES = 1024
REPLY_ROUTE = "/api/reply"
CATCH_UP_ROUTE = "/api/catch-up"


async def _a_page_that_stops_reading(review: RunningReview) -> socket.socket:
    """Open the review's session socket as a page would, read the handshake's answer, and read nothing more."""
    page = socket.socket()
    page.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, PAGE_RECEIVE_BUFFER)
    page.setblocking(False)
    loop = asyncio.get_running_loop()
    await loop.sock_connect(page, (LOOPBACK, review.port))
    key = base64.b64encode(os.urandom(HANDSHAKE_KEY_BYTES)).decode()
    handshake = (
        f"GET {SESSION_ROUTE} HTTP/1.1\r\nHost: {LOOPBACK}:{review.port}\r\n"
        f"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
    )
    await loop.sock_sendall(page, handshake.encode())
    await loop.sock_recv(page, HANDSHAKE_ANSWER_BYTES)
    return page


async def test_a_page_that_stops_reading_is_let_go(servers: ReviewServers, logged: list[EventDict]) -> None:
    review = await servers.start([], mode=ReviewMode.FILES)
    page = await _a_page_that_stops_reading(review)

    async with AsyncClient(base_url=review.url) as agent:
        for _ in range(ANSWER_COUNT):
            await agent.post(REPLY_ROUTE, json={"thread_id": "comment-1", "body": ANSWER})
        still_there = await agent.get(CATCH_UP_ROUTE)

    page.close()
    assert "page_fell_behind" in [entry["event"] for entry in logged]
    assert still_there.status_code == 200, "a page that stopped reading must not stop the review"

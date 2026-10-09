"""The server one review runs on: it ends with the review, and a server that never came up says so."""

import asyncio
import socket

import pytest

from claude_review.domain.models import ReviewMode
from claude_review.hosting.address import LOOPBACK
from claude_review.hosting.ports import ANY_FREE_PORT
from claude_review.hosting.review_server import ReviewServer, ServerStartError
from claude_review.services.review_lifetime import EndReason, ReviewLifetime
from tests.helpers import SETTLE_SECONDS, ReviewFactory


def _listening() -> socket.socket:
    listening = socket.socket()
    listening.bind((LOOPBACK, ANY_FREE_PORT))
    listening.listen()
    return listening


async def test_the_server_stops_once_the_review_ends(reviews: ReviewFactory) -> None:
    lifetime = ReviewLifetime()
    server = ReviewServer(reviews.app([], mode=ReviewMode.FILES), lifetime)
    serving = asyncio.ensure_future(server.serve_until_ended(_listening()))
    assert await server.came_up()

    lifetime.end(EndReason.FINISHED)

    await asyncio.wait_for(serving, timeout=SETTLE_SECONDS)
    assert lifetime.reason == EndReason.FINISHED


async def test_a_server_that_cannot_listen_ends_the_review_and_says_it_never_came_up(reviews: ReviewFactory) -> None:
    """A review nobody can open must end, and say why, rather than wait for a browser that cannot come."""
    lifetime = ReviewLifetime()
    server = ReviewServer(reviews.app([], mode=ReviewMode.FILES), lifetime)
    closed = _listening()
    closed.close()

    await asyncio.wait_for(server.serve_until_ended(closed), timeout=SETTLE_SECONDS)

    assert not await server.came_up()
    assert lifetime.reason == EndReason.SERVER_STOPPED
    with pytest.raises(ServerStartError):
        server.raise_if_it_never_came_up()

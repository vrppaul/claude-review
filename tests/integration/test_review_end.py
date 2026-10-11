"""How a review's end reaches its pages, against the server it really runs on.

The review ends, and its server stops a moment after: whatever the pages
are told of the end must reach them before their sockets close under them.
"""

import asyncio

from httpx import AsyncClient

from claude_review.presentation.wire.pushes import EndedPush
from claude_review.presentation.wire.session import Delivery, Welcome
from tests.helpers import SETTLE_SECONDS, ReviewServers, message_said, one_line_file, opening_of
from tests.page_socket import PageSocket, page_socket_held

END_ROUTE = "/api/end"


async def _next_message(page: PageSocket) -> str:
    """What the review says next down the page's socket, read off the loop the review answers on."""
    return await asyncio.to_thread(page.receive, timeout=SETTLE_SECONDS)


async def test_a_page_hears_the_review_is_over_before_its_socket_closes(servers: ReviewServers) -> None:
    review = await servers.start(opening_of([one_line_file()]))

    async with page_socket_held(review.port) as page, AsyncClient(base_url=review.url) as reader:
        assert isinstance(message_said(await _next_message(page)), Welcome)

        await reader.post(END_ROUTE)
        told = message_said(await _next_message(page))

    assert isinstance(told, Delivery)
    assert told.push == EndedPush(finished=True)

"""The socket a review's page holds open for as long as the review is on screen.

The socket is the signal: while one is open the review is being read, and
when the last one closes for good the review ends. It carries what the
review tells its pages one way, and what only the page knows the other.
Both directions run side by side, and either one ending ends the socket.
"""

import asyncio

import structlog
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from claude_review.presentation.broadcast import BrowserBroadcast
from claude_review.presentation.dependencies import get_broadcast, get_review
from claude_review.presentation.schemas import HeldThreads, ReceivedHello
from claude_review.services.review.review import Review

log = structlog.get_logger()

router = APIRouter()

# What a page that fell too far behind is told as its socket closes: come
# back later (RFC 6455, 7.4.1). It reconnects, and reads the review afresh.
FELL_BEHIND = 1013

# The ASGI message a socket receives once the page has gone
SOCKET_GONE = "websocket.disconnect"


@router.websocket("/session")
async def session(
    websocket: WebSocket,
    review: Review = Depends(get_review),
    broadcast: BrowserBroadcast = Depends(get_broadcast),
) -> None:
    """Hold the review open for as long as the page has it on screen, and tell the page what happens."""
    await websocket.accept()
    with review.presence.page_open():
        outbox = broadcast.listen(first=review.news_for_a_new_page())
        try:
            async with asyncio.TaskGroup() as directions:
                telling = directions.create_task(_tell_the_page(outbox, websocket))
                await _hear_the_page(review, websocket)
                # The page has gone: nothing is left to tell it
                telling.cancel()
        except* WebSocketDisconnect:
            log.debug("page_socket_lost")
        finally:
            broadcast.stop_listening(outbox)


async def _tell_the_page(outbox: asyncio.Queue[str], websocket: WebSocket) -> None:
    """Send down the socket everything told to the page, until the page falls too far behind."""
    while True:
        try:
            said = await outbox.get()
        except asyncio.QueueShutDown:
            await websocket.close(code=FELL_BEHIND)
            return
        await websocket.send_text(said)


async def _hear_the_page(review: Review, websocket: WebSocket) -> None:
    """Take what the page says until it goes. It says only text; anything else is passed over."""
    while (message := await websocket.receive())["type"] != SOCKET_GONE:
        said = message.get("text")
        if said is None:
            log.debug("page_frame_ignored")
            continue
        _catch_up(review, said)


def _catch_up(review: Review, said: str) -> None:
    """Take what the page knows and the review does not.

    Two things. The round: a review restarted mid-way comes back believing
    it is round one, so the page says where it had got to. And the threads:
    they are unsent work, held in that page, and an agent attaching later
    has no other way to learn they exist.
    """
    try:
        heard = ReceivedHello.model_validate_json(said)
    except ValidationError as error:
        # The socket is a lifeline first; nonsense on it is not worth
        # dropping a review over, but worth a line for whoever debugs it
        log.debug("hello_refused", errors=error.error_count())
        return

    if heard.round is not None:
        review.rounds.catch_up(heard.round)

    if heard.threads is not None:
        held = HeldThreads.read(heard.threads)
        review.threads.hold([thread.draft() for thread in held.readable], held.unreadable_ids)

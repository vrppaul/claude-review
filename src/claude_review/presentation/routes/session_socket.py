"""The socket a review's page holds open for as long as the review is on screen.

The socket is the signal: while one is open the review is being read, and
when the last one closes for good the review ends. It carries what the
review tells its pages one way, and what only the page knows the other.
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
        pump = asyncio.create_task(_forward(outbox, websocket))
        try:
            while True:
                # The page says where the review had got to, and otherwise
                # this waits for the close
                _catch_up(review, await websocket.receive_text())
        except WebSocketDisconnect:
            pass
        finally:
            pump.cancel()
            broadcast.stop_listening(outbox)


async def _forward(outbox: asyncio.Queue[str], websocket: WebSocket) -> None:
    """Send down the socket everything pushed to it, for as long as it is open."""
    while True:
        await websocket.send_text(await outbox.get())


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

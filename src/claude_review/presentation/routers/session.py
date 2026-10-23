"""The socket a review's page holds open for as long as the review is on screen.

The socket is the signal: while one is open the review is being read, and
when the last one closes for good the review ends. It carries what the
review tells its pages one way, and what only the page knows the other.
Both directions run side by side, and either one ending ends the socket.
"""

import asyncio
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from claude_review.presentation.asgi import WEBSOCKET_DISCONNECT
from claude_review.presentation.broadcast import BrowserBroadcast
from claude_review.presentation.dependencies import BroadcastDep, ReviewDep
from claude_review.presentation.schemas.session import PushNumber, Resume, ReviewName, RunName
from claude_review.presentation.schemas.threads import NamedThread, ReceivedHello, ThreadDraft
from claude_review.services.review.review import Review

log = structlog.get_logger()

router = APIRouter()

# What a page that fell too far behind is told as its socket closes: come
# back later (RFC 6455, 7.4.1). A page still there reconnects, and is handed
# what it missed if the review still keeps it.
FELL_BEHIND = 1013


def _resume_named(
    identity: ReviewName | None = None, instance: RunName | None = None, after: PushNumber | None = None
) -> Resume | None:
    """Where the page had got to, as its socket's address names it; nothing from a page still reading its review."""
    if identity is None or instance is None or after is None:
        return None
    return Resume(identity=identity, instance=instance, after=after)


@router.websocket("/session")
async def session(
    websocket: WebSocket,
    resume: Annotated[Resume | None, Depends(_resume_named)],
    review: ReviewDep,
    broadcast: BroadcastDep,
) -> None:
    """Hold the review open for as long as the page has it on screen, and tell the page what happens.

    A page names the review it reads, the run of it and how far it had got
    in it — by the pushes it took in, the facts it read, or the draft it
    opened from — and is handed what came after. One that names nothing yet
    only holds the review on screen while it opens. One that names another
    review was left open on a review that ran on this port before: it is
    not this review's page, and is told so and let go before it counts as one.
    """
    await websocket.accept()
    if resume is not None and not review.answers_to(resume.identity):
        await _turn_away(websocket, broadcast)
        return
    with review.page_open():
        outbox = broadcast.listen(resume=resume)
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


async def _turn_away(websocket: WebSocket, broadcast: BrowserBroadcast) -> None:
    """Tell a page of another review which review answers here, and let it go: its own is over."""
    log.debug("page_of_another_review_turned_away")
    try:
        await websocket.send_text(broadcast.welcome_alone())
        await websocket.close()
    except WebSocketDisconnect:
        # The page hung up first, as one does on reading the welcome: nobody is left to tell
        log.debug("page_socket_lost")


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
    while (message := await websocket.receive())["type"] != WEBSOCKET_DISCONNECT:
        said = message.get("text")
        if said is None:
            log.debug("page_frame_ignored")
            continue
        _take_the_hello(review, said)


def _take_the_hello(review: Review, said: str) -> None:
    """Take what the page knows and the review does not.

    Two things. The round: a review restarted mid-way that lost what it kept
    comes back believing it is round one, so the page says where it had got
    to. And the threads: they are unsent work, held in that page, and an
    agent attaching later has no other way to learn they exist.
    """
    try:
        heard = ReceivedHello.model_validate_json(said)
    except ValidationError as error:
        # The socket is a lifeline first: nonsense on it is not worth
        # dropping a review over, but the round and the threads it carried
        # are lost
        log.warning("hello_refused", errors=error.error_count())
        return

    if heard.round is not None:
        review.page_reached_round(heard.round)

    if heard.threads is not None:
        drafts = [thread for thread in heard.threads if isinstance(thread, ThreadDraft)]
        named_ids = [thread.thread_id for thread in heard.threads if isinstance(thread, NamedThread)]
        # Not even an id could be read of the rest, so nothing of them is held but how many there are
        unnamed_count = len(heard.threads) - len(drafts) - len(named_ids)
        review.page_holds([draft.to_domain() for draft in drafts], named_ids, unnamed_count=unnamed_count)

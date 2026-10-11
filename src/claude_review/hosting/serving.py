"""Holding a review open on this machine until it ends, and what it hands back when it does.

Four things run while a review is open, and the review ending stops all of
them: the server, the word to whoever started it that it is listening, the
check that its page is still open, and the watch on the working tree.
Whichever way it ends — sent, closed, Ctrl+C or `kill`, the server stopping,
a fault — the way out is the same: the directories it wrote go, and the last
round is handed back. Ctrl+C and `kill` are answered from the moment the
review starts to open, so one that arrives before it runs still leaves
nothing behind.
"""

import asyncio
import contextlib
import signal
import socket
from collections.abc import Coroutine, Generator

import structlog

from claude_review.hosting.address import review_url
from claude_review.hosting.announcer import ReviewAnnouncer
from claude_review.hosting.errors import ReviewStoppedError
from claude_review.hosting.hosted_review import host_review
from claude_review.hosting.ports import bind, stable_port
from claude_review.hosting.review_server import ReviewServer
from claude_review.hosting.workspace import reader_files, review_workspace
from claude_review.repositories.system_clock import SystemClock
from claude_review.services.review.review import Review
from claude_review.services.review.review_lifetime import EndReason, ReviewLifetime
from claude_review.services.review_opening import ReviewOpening

log = structlog.get_logger()

# What stops a review the way closing it does: Ctrl+C, and `kill`
STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)


class StopSignals:
    """What Ctrl+C and `kill` stop, from the moment a review starts to open until it is over.

    Never the process where it stands, which would leave behind what the
    review wrote. While the review opens there is no review to end, only
    the work of opening it: that is cancelled, and leaves through every
    `finally` on its way — the staging's, which removes what it wrote, among
    them. Once the review runs, a signal ends it the way closing it does,
    and its last round is still handed back; once it has ended, a signal
    finds nothing left to stop.
    """

    def __init__(self, launch: asyncio.Task[object]) -> None:
        self._launch = launch
        # The review, once it runs
        self._lifetime: ReviewLifetime | None = None
        # Whether a signal cancelled the opening, rather than anything else
        self._stopped_opening = False

    @property
    def stopped_opening(self) -> bool:
        """Whether a signal cancelled the work of opening the review."""
        return self._stopped_opening

    def hand_to(self, lifetime: ReviewLifetime) -> None:
        """From now on, a signal ends this review rather than the work of opening it."""
        self._lifetime = lifetime

    def stop(self) -> None:
        """Answer a signal: end the review if one runs, stop its opening if not."""
        if self._lifetime is not None:
            self._lifetime.end(EndReason.STOPPED)
            return
        self._stopped_opening = True
        self._launch.cancel()


@contextlib.contextmanager
def stop_signals() -> Generator[StopSignals]:
    """Answer Ctrl+C and `kill` for as long as this lasts, in the task it is entered in, as `StopSignals` says.

    Raises:
        ReviewStoppedError: if a signal stopped the review before it ran.
    """
    launch = asyncio.current_task()
    if launch is None:
        msg = "a review is launched in a task, which is what a signal stops"
        raise RuntimeError(msg)
    signals = StopSignals(launch)
    loop = asyncio.get_running_loop()
    for stop_signal in STOP_SIGNALS:
        loop.add_signal_handler(stop_signal, signals.stop)
    try:
        yield signals
    except asyncio.CancelledError:
        # Cancelled by a signal, and by nothing else that is still waiting to
        # be told: the cancellation is this one's to turn into a stop
        if not signals.stopped_opening or launch.uncancel() > 0:
            raise
        msg = "the review was stopped before it opened"
        raise ReviewStoppedError(msg) from None
    finally:
        for stop_signal in STOP_SIGNALS:
            loop.remove_signal_handler(stop_signal)


async def serve_review(
    opening: ReviewOpening, *, port: int | None, announcer: ReviewAnnouncer, signals: StopSignals
) -> str:
    """Hold a review open until it ends, and return what it hands back: its rounds, and anything left unread.

    `port` is the one asked for; None works it out from what is reviewed, so
    the review comes back on the same one whenever it is opened again.

    Raises:
        PortUnavailableError: If the port asked for is taken.
        ServerStartError: If the server stopped before it ever listened.
    """
    with review_workspace(writes_trees=opening.repository is not None, announcer=announcer) as workspace:
        hosted = host_review(opening, workspace=workspace, reader_files=reader_files(), clock=SystemClock())
        review = hosted.review
        signals.hand_to(review.lifetime)
        server = ReviewServer(hosted.app, review.lifetime)
        listening = bind(port if port is not None else stable_port(opening.identity), may_fall_back=port is None)
        try:
            await _run_until_ended(server, listening, review, announcer)
        finally:
            listening.close()
            # Before the workspace says what it leaves behind: only what was sent
            await review.discard_unsent_images()

        server.raise_if_it_never_came_up()
        return review.exit_report()


async def _run_until_ended(
    server: ReviewServer, listening: socket.socket, review: Review, announcer: ReviewAnnouncer
) -> None:
    """Run everything a review open on screen needs, until the review ends and every one of them has stopped.

    The server is the review. Saying where it is and noticing its page close
    are what it cannot do without: one of them failing ends the review, the
    last round handed back. The watch on the tree only helps: it failing
    leaves the review running.
    """
    url = review_url(listening.getsockname()[1])
    lifetime = review.lifetime
    async with asyncio.TaskGroup() as tasks:
        tasks.create_task(server.serve_until_ended(listening))
        tasks.create_task(_needed(_announce_once_listening(server, url, announcer), lifetime))
        tasks.create_task(_needed(review.end_once_its_page_is_closed(), lifetime))
        tasks.create_task(_helping(review.tell_when_the_tree_moves()))


async def _needed(work: Coroutine[object, object, None], lifetime: ReviewLifetime) -> None:
    """Run something the review cannot do without, and end the review if it fails.

    Said at critical, the level a review that is otherwise quiet still says.
    """
    try:
        await work
    except Exception:
        log.critical("review_part_failed", part=work.__qualname__, exc_info=True)
        lifetime.end(EndReason.FAULT)


async def _helping(work: Coroutine[object, object, None]) -> None:
    """Run something that only helps the review, and let the review go on without it if it fails."""
    try:
        await work
    except Exception:
        log.critical("review_helper_failed", helper=work.__qualname__, exc_info=True)


async def _announce_once_listening(server: ReviewServer, url: str, announcer: ReviewAnnouncer) -> None:
    """Tell whoever started the review where it is, once it listens."""
    if await server.came_up():
        log.info("server_started", url=url)
        await announcer.listening_at(url)

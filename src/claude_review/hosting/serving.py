"""Holding a review open on this machine until it ends, and what it hands back when it does.

Four things run while a review is open, and the review ending stops all of
them: the server, the word to whoever started it that it is listening, the
check that its page is still open, and the watch on the working tree.
Whichever way it ends — sent, closed, Ctrl+C or `kill`, the server stopping,
a fault — the way out is the same: the directories it wrote go, and the last
round is handed back.
"""

import asyncio
import contextlib
import signal
import socket
from collections.abc import Coroutine, Generator
from pathlib import Path

import structlog
from fastapi import FastAPI

from claude_review.domain.models import ReviewWorkspace
from claude_review.domain.protocols import Clock
from claude_review.hosting.address import review_url
from claude_review.hosting.announcer import ReviewAnnouncer
from claude_review.hosting.ports import bind, stable_port
from claude_review.hosting.review_server import ReviewServer
from claude_review.hosting.workspace import reader_files, review_workspace
from claude_review.presentation.app import create_app
from claude_review.presentation.schemas import ChangedPush
from claude_review.presentation.state import ServerState
from claude_review.repositories.git_repository import GitRepository
from claude_review.repositories.system_clock import SystemClock
from claude_review.services.exit_report import exit_report
from claude_review.services.review_lifetime import EndReason, ReviewLifetime
from claude_review.services.review_opening import ReviewOpening
from claude_review.services.tree_watcher_service import TreeWatcherService
from claude_review.services.version_service import VersionService

log = structlog.get_logger()

# How long the review may have no page open before it ends. A reload drops
# the socket and takes it again within a moment.
DISCONNECT_GRACE = 3.0
# How often the review looks whether its page is still open
PRESENCE_CHECK_SECONDS = 0.5

# What stops a review the way closing it does: Ctrl+C, and `kill`
STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)


async def serve_review(opening: ReviewOpening, *, port: int | None, announcer: ReviewAnnouncer) -> str:
    """Hold a review open until it ends, and return what it hands back: its rounds, and anything left unread.

    `port` is the one asked for; None works it out from what is reviewed, so
    the review comes back on the same one whenever it is opened again.

    Raises:
        PortUnavailableError: If the port asked for is taken.
        ServerStartError: If the server stopped before it ever listened.
    """
    with review_workspace(writes_trees=opening.root is not None, announcer=announcer) as workspace:
        clock = SystemClock()
        state = ServerState(ReviewLifetime())
        # The review's own repository, which writes the trees it is read
        # against into the review's workspace rather than the one under review
        git = GitRepository(objects=workspace.objects)
        watcher = TreeWatcherService(git_repository=git)
        if opening.root is not None:
            await _note_the_opening_tree(state, watcher, VersionService(git_repository=git, clock=clock), opening.root)

        server = ReviewServer(_review_app(opening, state, workspace, clock), state.lifetime)
        listening = bind(port if port is not None else stable_port(opening.identity), may_fall_back=port is None)
        try:
            await _run_until_ended(server, listening, state, watcher, opening.root, announcer)
        finally:
            listening.close()

        server.raise_if_it_never_came_up()
        return exit_report(state.last_round, state.inbox.drain())


def _review_app(opening: ReviewOpening, state: ServerState, workspace: ReviewWorkspace, clock: Clock) -> FastAPI:
    """The app serving this review: its page, and the routes its page and its agent call."""
    return create_app(
        diff_files=opening.diff_files,
        state=state,
        mode=opening.mode,
        title=opening.title,
        workspace=workspace,
        reader_files=reader_files(),
        clock=clock,
        root=opening.root,
        base=opening.base,
    )


async def _note_the_opening_tree(
    state: ServerState, watcher: TreeWatcherService, versions: VersionService, root: Path
) -> None:
    """Note the tree the review opens on: what the watcher compares against, and a base rounds can go back to."""
    state.tree = await watcher.read(root)
    opened_at = await versions.take(root, round_number=state.round)
    if opened_at is not None:
        state.snapshots.append(opened_at)


async def _run_until_ended(
    server: ReviewServer,
    listening: socket.socket,
    state: ServerState,
    watcher: TreeWatcherService,
    root: Path | None,
    announcer: ReviewAnnouncer,
) -> None:
    """Run everything a review open on screen needs, until the review ends and every one of them has stopped.

    The server is the review. Saying where it is and noticing its page close
    are what it cannot do without: one of them failing ends the review, the
    last round handed back. The watch on the tree, which only a review of a
    repository has, only helps: it failing leaves the review running.
    """
    url = review_url(listening.getsockname()[1])
    lifetime = state.lifetime
    with _ended_by_signals(lifetime):
        async with asyncio.TaskGroup() as tasks:
            tasks.create_task(server.serve_until_ended(listening))
            tasks.create_task(_needed(_announce_once_listening(server, url, announcer), lifetime))
            tasks.create_task(_needed(_end_once_the_page_is_closed(state), lifetime))
            if root is not None:
                tasks.create_task(_helping(_tell_when_the_tree_moves(state, watcher, root)))


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


async def _end_once_the_page_is_closed(state: ServerState) -> None:
    """End the review once its page has been closed rather than reloaded: for everyone, an agent waiting included."""
    loop = asyncio.get_running_loop()
    while not await state.lifetime.ended_within(PRESENCE_CHECK_SECONDS):
        if state.browser_gone(loop.time(), DISCONNECT_GRACE):
            state.lifetime.end(EndReason.BROWSER_CLOSED)


async def _tell_when_the_tree_moves(state: ServerState, watcher: TreeWatcherService, root: Path) -> None:
    """Say when the tree stops matching the diff. Never act on it: the reader decides when to take the diff again."""
    async for moved in watcher.changes(root, taken_at=lambda: state.tree, lifetime=state.lifetime):
        state.push(ChangedPush(moved_count=moved))


@contextlib.contextmanager
def _ended_by_signals(lifetime: ReviewLifetime) -> Generator[None]:
    """End the review on Ctrl+C or `kill` the way closing it ends it."""
    loop = asyncio.get_running_loop()
    for stop_signal in STOP_SIGNALS:
        loop.add_signal_handler(stop_signal, lifetime.end, EndReason.STOPPED)
    try:
        yield
    finally:
        for stop_signal in STOP_SIGNALS:
            loop.remove_signal_handler(stop_signal)

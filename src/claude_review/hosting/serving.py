"""Holding a review open on this machine until it ends, and what it hands back when it does.

Four things run while a review is open, and the review ending stops all of
them: the server, the line that says where it is, the check that its page is
still open, and the watch on the working tree. Whichever way it ends — sent,
closed, Ctrl+C or `kill`, the server stopping — the way out is the same: the
directories it wrote go, and the last round is handed back.
"""

import asyncio
import contextlib
import signal
import socket
import webbrowser
from collections.abc import Coroutine, Generator
from pathlib import Path
from typing import Any

import click
import structlog
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import ReviewWorkspace
from claude_review.domain.protocols import Clock
from claude_review.hosting.address import review_url
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

# How the review says where it is, on stderr: whoever started it in the
# background reads the address from this line
READY_ANNOUNCEMENT = "Review ready at "


class LaunchOptions(BaseModel):
    """How a review is launched, apart from what it opens on."""

    model_config = ConfigDict(frozen=True)

    # The port asked for; None leaves it to be worked out from what is reviewed
    port: int | None
    open_browser: bool


async def serve_review(opening: ReviewOpening, options: LaunchOptions) -> str:
    """Hold a review open until it ends, and return what it hands back: its rounds, and anything left unread.

    Raises:
        PortUnavailableError: If the port asked for is taken.
        ServerStartError: If the server stopped before it ever listened.
    """
    with review_workspace(writes_trees=opening.root is not None) as workspace:
        clock = SystemClock()
        state = ServerState(ReviewLifetime())
        git = GitRepository(objects=workspace.objects)
        watcher = TreeWatcherService(git_repository=git)
        if opening.root is not None:
            await _note_the_opening_tree(state, watcher, VersionService(git_repository=git, clock=clock), opening.root)

        server = ReviewServer(_review_app(opening, state, workspace, clock), state.lifetime)
        listening = bind(_port_to_take(opening, options), may_fall_back=options.port is None)
        try:
            await _run_until_ended(
                server, listening, state, watcher, root=opening.root, open_browser=options.open_browser
            )
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


def _port_to_take(opening: ReviewOpening, options: LaunchOptions) -> int:
    """The port asked for, or the one this review comes back on whenever it is opened again."""
    return options.port if options.port is not None else stable_port(opening.identity)


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
    *,
    root: Path | None,
    open_browser: bool,
) -> None:
    """Run everything a review open on screen needs, until the review ends and every one of them has stopped.

    The server is the review; the rest only help it, and one of them failing
    must not take the server down with the reader's unsent work on screen,
    nor keep the last round from being handed back. The tree is watched only
    in a review of a repository, whose `root` it is.
    """
    url = review_url(listening.getsockname()[1])
    with _ended_by_signals(state.lifetime):
        async with asyncio.TaskGroup() as tasks:
            tasks.create_task(server.serve_until_ended(listening))
            tasks.create_task(_helping(_announce_once_listening(server, url, open_browser=open_browser)))
            tasks.create_task(_helping(_end_once_the_page_is_closed(state)))
            if root is not None:
                tasks.create_task(_helping(_tell_when_the_tree_moves(state, watcher, root)))


async def _helping(work: Coroutine[Any, Any, None]) -> None:
    """Run something that helps the review, and let the review go on without it if it fails.

    Said at critical, the level a review that is otherwise quiet still says.
    """
    try:
        await work
    except Exception:
        log.critical("review_helper_failed", helper=work.__qualname__, exc_info=True)


async def _announce_once_listening(server: ReviewServer, url: str, *, open_browser: bool) -> None:
    """Say where the review is once it listens, and open it if asked.

    Said either way. Opening a window and saying where the review is are two
    different jobs, and tying them together meant that anything starting a
    review for somebody else had to refuse the window to learn the address —
    so nobody's browser ever opened.
    """
    if not await server.came_up():
        return
    log.info("server_started", url=url)
    click.echo(f"{READY_ANNOUNCEMENT}{url}", err=True)
    if open_browser:
        await asyncio.to_thread(_open_browser, url)


def _open_browser(url: str) -> None:
    """Open the review, and let it go if there is nothing to open it with.

    A machine with no browser — over ssh, in a container, in CI — must not
    lose its review over the attempt. The address has already been printed,
    which is the way in either way.
    """
    try:
        webbrowser.open_new(url)
    except webbrowser.Error:
        log.info("no_browser", url=url)


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

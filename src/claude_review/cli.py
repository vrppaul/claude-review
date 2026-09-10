"""CLI entry point for claude-review."""

import asyncio
import hashlib
import json
import logging
import socket
import sys
import urllib.error
import urllib.request
import webbrowser
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

import click
import structlog
import uvicorn

from claude_review.domain.exceptions import PortUnavailableError
from claude_review.domain.models import DiffFile, ReviewMode
from claude_review.presentation.app import create_app
from claude_review.presentation.state import ServerState
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_service import DiffService
from claude_review.services.text_file_service import TextFileService
from claude_review.services.transcript_service import TranscriptService
from claude_review.services.tree_watcher_service import TreeWatcherService

log = structlog.get_logger()

# How long the review may have no browser attached before the server winds
# down. A reload drops the socket and takes it again within a moment.
DISCONNECT_GRACE = 3.0

# Where derived ports live: above the well-known and registered services,
# below the ephemeral range the kernel hands out.
STABLE_PORT_FLOOR = 40_000
STABLE_PORT_CEILING = 60_000


def _configure_logging(*, verbose: bool = False) -> None:
    """Configure structlog. Silent by default, stderr output with --verbose."""
    level = logging.INFO if verbose else logging.CRITICAL
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )


async def _load_diff(repo_path: Path, base: str | None = None) -> tuple[list[DiffFile], Path]:
    """Load diff files from a git repository, and say where its root is.

    Git reports paths relative to the repository root rather than to the
    directory it was run in, so anything that resolves those paths later —
    expanding a hunk's context — has to be told the root, not the argument.
    """
    git_repo = GitRepository()
    diff_service = DiffService(git_repository=git_repo)
    log.info("loading_diff", path=str(repo_path), base=base)
    files = await diff_service.get_diff(repo_path, base=base)
    return files, await git_repo.top_level(repo_path) or repo_path


async def _serve(
    diff_files: list[DiffFile],
    mode: ReviewMode,
    port: int,
    title: str,
    *,
    root: Path | None = None,
    base: str | None = None,
    open_browser: bool = True,
    may_fall_back: bool = False,
) -> str:
    """Start the review server and return formatted review markdown."""
    state = ServerState(shutdown_event=asyncio.Event())
    app = create_app(diff_files=diff_files, state=state, mode=mode, title=title, root=root, base=base)

    watcher = TreeWatcherService(git_repository=GitRepository())
    if root is not None:
        state.tree = await watcher.read(root)

    # Bind before handing the socket to uvicorn: a port clash then surfaces here
    # as an OSError we can explain, instead of uvicorn calling sys.exit() from
    # inside the event loop and printing a traceback.
    sock = _bind(port, may_fall_back=may_fall_back)
    url = f"http://127.0.0.1:{sock.getsockname()[1]}"

    # The default picks uvicorn's older websockets integration, which warns on
    # every connection with websockets 14 and later
    config = uvicorn.Config(app, log_level="error", ws="websockets-sansio")
    server = uvicorn.Server(config)

    async def wait_for_shutdown() -> None:
        for _ in range(100):  # 5 second startup timeout
            if server.started:
                break
            await asyncio.sleep(0.05)
        if not server.started:
            log.error("server_start_timeout")
            server.should_exit = True
            return

        log.info("server_started", url=url)

        if open_browser:
            await asyncio.to_thread(_open_browser, url)
        else:
            # Nothing else will say where the review is
            sys.stderr.write(f"Review ready at {url}\n")
            sys.stderr.flush()

        while not state.shutdown_event.is_set():
            await asyncio.sleep(0.5)
            if state.browser_gone(asyncio.get_running_loop().time(), DISCONNECT_GRACE):
                log.info("browser_closed")
                break

        server.should_exit = True
        log.info("server_shutting_down")

    async def watch_tree() -> None:
        """Say when the tree stops matching the diff. Never act on it: the
        reader decides when to take the diff again."""
        if root is None:
            return
        async for moved in watcher.changes(root, taken_at=lambda: state.tree, stop=state.shutdown_event):
            state.push({"type": "changed", "files": moved})

    # A task rather than a third thing to gather: the watcher has no end of
    # its own, and the review is over when the server is, not when the tree
    # stops moving.
    watching = asyncio.create_task(watch_tree())
    try:
        await asyncio.gather(server.serve(sockets=[sock]), wait_for_shutdown())
    finally:
        watching.cancel()
        sock.close()

    return state.result or ""


def _bind(port: int, *, may_fall_back: bool = False) -> socket.socket:
    """Take the loopback port the server will listen on.

    Raises:
        PortUnavailableError: If a port that was asked for is already taken.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("127.0.0.1", port))
    except OSError as e:
        sock.close()
        if may_fall_back:
            # Nobody asked for this port; it was worked out from what is
            # being reviewed. Something else holding it is not the reader's
            # problem, and a review on any port beats no review.
            log.info("derived_port_taken", port=port)
            return _bind(0)
        msg = f"port {port} is already in use — pass a different --port, or omit it to pick a free one"
        raise PortUnavailableError(msg) from e
    sock.listen(128)
    return sock


def _stable_port(root: Path, base: str | None) -> int:
    """Work out which port this review should come back on.

    A review reopened on the same thing should land on the same origin: an
    unsent draft lives in the browser's storage, which is keyed by origin,
    so a fresh port every time throws away the comments of whoever closed
    the tab and opened the review again.
    """
    seed = f"{root.resolve()}\n{base or ''}".encode()
    span = STABLE_PORT_CEILING - STABLE_PORT_FLOOR
    return STABLE_PORT_FLOOR + int.from_bytes(hashlib.blake2s(seed, digest_size=4).digest()) % span


def _diff_title(repo_path: Path, base: str | None) -> str:
    """Name the repository under review and what it is compared against."""
    where = repo_path.name or str(repo_path)
    against = f"changes since {base}" if base else "uncommitted changes"
    return f"{where}: {against}"


def _files_title(paths: list[Path]) -> str:
    return f"{len(paths)} file{'' if len(paths) == 1 else 's'}"


def _transcript_title(path: Path) -> str:
    return f"Conversation {path.stem}"


def _call(url: str, *, payload: dict | None = None, timeout: float = 10.0) -> str:
    """Talk to a review server, and explain it plainly when that fails.

    These commands are driven from a loop, where a traceback out of urllib
    says nothing about what went wrong or what to do next.
    """
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace").strip()
        msg = f"the review refused this ({e.code}): {detail or e.reason}"
        raise click.ClickException(msg) from e
    except urllib.error.URLError as e:
        msg = f"no review is listening there: {e.reason}"
        raise click.ClickException(msg) from e
    except TimeoutError as e:
        msg = "the review did not answer in time"
        raise click.ClickException(msg) from e


def _open_browser(url: str) -> None:
    webbrowser.open_new(url)


def _print_result(result: str) -> None:
    """Write review result to stdout if non-empty."""
    if result:
        sys.stdout.write(result)
        sys.stdout.write("\n")


def _run_review(session: Coroutine[Any, Any, str]) -> None:
    """Run a review session and print its result.

    A port clash becomes a ClickException so the user gets one line of
    explanation rather than a traceback out of the event loop.
    """
    try:
        _print_result(asyncio.run(session))
    except PortUnavailableError as e:
        raise click.ClickException(str(e)) from e


@click.group()
@click.version_option(package_name="claude-review")
@click.option(
    "--port", default=0, type=int, help="Port to run the server on. Derived from what is reviewed if omitted."
)
@click.option("--no-open", is_flag=True, help="Don't open the browser automatically.")
@click.option("--verbose", is_flag=True, help="Enable diagnostic logging to stderr.")
@click.pass_context
def main(ctx: click.Context, port: int, no_open: bool, verbose: bool) -> None:
    """Browser-based code review tool for Claude Code."""
    _configure_logging(verbose=verbose)
    ctx.ensure_object(dict)
    ctx.obj["port"] = port
    ctx.obj["open_browser"] = not no_open


@main.command("wait")
@click.option("--port", required=True, type=int, help="Port the review is served on.")
@click.option(
    "--seconds",
    default=25.0,
    type=float,
    help="How long to wait before reporting that nothing was asked.",
)
def wait_cmd(port: int, seconds: float) -> None:
    """Wait for whatever the reader hands over next.

    Prints one JSON object and exits, so a caller can loop: a "question"
    about a thread, answered with `claude-review reply`; a "message" from
    the agent panel, answered with `claude-review say`; a "round" of the
    review; a "cancel" taking a message back; "timeout" if nothing was said,
    or "closed" once the review is over.
    """
    body = _call(
        f"http://127.0.0.1:{port}/api/events?wait_seconds={seconds}",
        timeout=seconds + 10,
    )
    sys.stdout.write(body)
    sys.stdout.write("\n")


@main.command("reply")
@click.option("--port", required=True, type=int, help="Port the review is served on.")
@click.option("--thread", required=True, type=str, help="Thread the answer belongs to.")
@click.option(
    "--question",
    type=str,
    default=None,
    help="Question being answered, from the event. Omitted, the oldest one still waiting takes it.",
)
@click.argument("text", required=True, type=str)
def reply_cmd(port: int, thread: str, question: str | None, text: str) -> None:
    """Answer a question the reader asked about a comment thread.

    A thread can have several questions waiting at once, so naming the one
    being answered is what puts the answer under it rather than under
    whatever was asked last.
    """
    _call(
        f"http://127.0.0.1:{port}/api/reply",
        payload={"thread_id": thread, "question_id": question, "text": text},
    )


@main.command("say")
@click.option("--port", required=True, type=int, help="Port the review is served on.")
@click.option(
    "--message",
    type=str,
    default=None,
    help="Message being answered, from the event. Omitted, this is you speaking first.",
)
@click.option(
    "--file",
    "files",
    multiple=True,
    help="A file worth opening at what you said. Repeatable; each becomes a chip the reader can jump by.",
)
@click.argument("text", required=True, type=str)
def say_cmd(port: int, message: str | None, files: tuple[str, ...], text: str) -> None:
    """Say something in the agent panel.

    The panel is where the review is discussed rather than any one line of
    it. Naming the message is what puts an answer under it: several can be
    waiting, and the reader is still reading while you write. Name nothing
    and you are speaking first — worth doing when you have finished
    something they are waiting on.
    """
    _call(
        f"http://127.0.0.1:{port}/api/say",
        payload={"message_id": message, "text": text, "files": list(files)},
    )


@main.command("progress")
@click.option("--port", required=True, type=int, help="Port the review is served on.")
@click.option("--message", type=str, default=None, help="Message being worked on, from the event.")
@click.option("--file", "files", multiple=True, help="A file being worked on. Repeatable.")
@click.option("--done", is_flag=True, help="Take the line away: the work is finished.")
@click.argument("text", required=False, type=str, default="")
def progress_cmd(port: int, message: str | None, files: tuple[str, ...], done: bool, text: str) -> None:
    """Say what you are doing, while you are doing it.

    Waiting says only that something is happening; this says what. Send it
    again to change it — it replaces what was showing rather than adding to
    it, because it is the state of the work and not a log of it. Send it
    with --done, or answer, and the line goes away.
    """
    _call(
        f"http://127.0.0.1:{port}/api/progress",
        payload={
            "message_id": message,
            "text": "" if done else text,
            "files": [] if done else list(files),
        },
    )


@main.command("show")
@click.option("--port", required=True, type=int, help="Port the review is served on.")
@click.option("--file", "path", required=True, type=str, help="File to bring into view, as the diff names it.")
def show_cmd(port: int, path: str) -> None:
    """Take the reader to a file, and mark it for a moment when they arrive.

    This moves somebody else's screen, so send it only when they asked to be
    taken somewhere. To offer a jump rather than make one, hang the file off
    what you say instead: `say --file <path>`.
    """
    _call(f"http://127.0.0.1:{port}/api/show", payload={"file": path})


@main.command("point")
@click.option("--port", required=True, type=int, help="Port the review is served on.")
@click.option("--file", "path", required=True, type=str, help="File the thread hangs on, as the diff names it.")
@click.option("--lines", required=True, type=str, help='Line or range it is about, e.g. "42" or "42-47".')
@click.option(
    "--side",
    type=click.Choice(["new", "old"]),
    default="new",
    help="Which version of the file: the new one, or the lines the change removed.",
)
@click.option(
    "--severity",
    type=click.Choice(["note", "question", "blocker"]),
    default="note",
    help="How it is meant to be taken.",
)
@click.argument("body", required=True, type=str)
def point_cmd(port: int, path: str, lines: str, side: str, severity: str, body: str) -> None:
    """Raise a thread on a line of the review, from this side.

    For what belongs on the code rather than in the panel: where you did
    something other than what was asked, and why. The reader reads it as an
    ordinary thread — answers it, settles it, removes it — but it is drawn
    as yours, and it is not counted as their unsent work.
    """
    start, end = _line_range(lines)
    body_text = _call(
        f"http://127.0.0.1:{port}/api/point",
        payload={
            "file": path,
            "side": side,
            "start_line": start,
            "end_line": end,
            "body": body,
            "severity": severity,
        },
    )
    sys.stdout.write(body_text)
    sys.stdout.write("\n")


def _line_range(lines: str) -> tuple[int, int]:
    """Read "42" or "42-47" as the span a thread hangs on."""
    start, _, end = lines.partition("-")
    try:
        first = int(start)
        last = int(end) if end else first
    except ValueError:
        msg = f'--lines wants a line or a range, like "42" or "42-47", not "{lines}"'
        raise click.ClickException(msg) from None
    if first < 1 or last < first:
        msg = f'--lines runs backwards or starts below 1: "{lines}"'
        raise click.ClickException(msg)
    return first, last


@main.command("status")
@click.option("--port", required=True, type=int, help="Port the review is served on.")
@click.option("--model", type=str, default=None, help="Which model is answering.")
@click.option(
    "--context",
    type=str,
    default=None,
    help='How much of the context window is spent, in your own words (e.g. "53% of 1M").',
)
def status_cmd(port: int, model: str | None, context: str | None) -> None:
    """Say what only this side can know, for the panel to show.

    The review can measure what handing it over costs, because it holds the
    diff. It cannot see into another process, so the model and the context
    are quoted from here, with the time they were said beside them. Say
    nothing and the panel shows nothing rather than a number that is a guess.
    """
    if model is None and context is None:
        msg = "nothing to report — pass --model, --context, or both"
        raise click.ClickException(msg)
    _call(
        f"http://127.0.0.1:{port}/api/status",
        payload={"model": model, "context": context},
    )


@main.command("round")
@click.option("--port", required=True, type=int, help="Port the review is served on.")
def round_cmd(port: int) -> None:
    """Take the diff again, after making the changes a round asked for.

    The reviews on screen reload it, keeping their threads: a comment whose
    lines survived follows them, and one whose lines are gone is marked
    outdated rather than pointing at whatever moved into their place.
    """
    body = _call(f"http://127.0.0.1:{port}/api/round", payload={})
    sys.stdout.write(body)
    sys.stdout.write("\n")


@main.command("diff")
@click.argument("path", required=False, type=click.Path(exists=True, path_type=Path))
@click.option(
    "--base", type=str, default=None, help="Compare against a specific commit (e.g., HEAD~3, abc123, v0.5.0)."
)
@click.pass_context
def diff_cmd(ctx: click.Context, path: Path | None, base: str | None) -> None:
    """Review git changes."""
    repo_path = (path or Path(".")).resolve()

    async def _run() -> str:
        diff_files, root = await _load_diff(repo_path, base=base)
        if not diff_files:
            sys.stderr.write("No changes found.\n")
            return ""
        log.info("content_loaded", file_count=len(diff_files), mode=ReviewMode.DIFF)
        asked_for = ctx.obj["port"]
        return await _serve(
            diff_files,
            ReviewMode.DIFF,
            asked_for or _stable_port(root, base),
            _diff_title(repo_path, base),
            root=root,
            base=base,
            open_browser=ctx.obj["open_browser"],
            may_fall_back=not asked_for,
        )

    _run_review(_run())


@main.command("files")
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True, path_type=Path))
@click.pass_context
def files_cmd(ctx: click.Context, paths: tuple[Path, ...]) -> None:
    """Review text files — plans, docs, configs, source code."""
    log.info("loading_files", count=len(paths))
    diff_files = TextFileService().read_files(list(paths))
    if not diff_files:
        sys.stderr.write("No content to review.\n")
        return
    log.info("content_loaded", file_count=len(diff_files), mode=ReviewMode.FILES)
    asked_for = ctx.obj["port"]
    _run_review(
        _serve(
            diff_files,
            ReviewMode.FILES,
            asked_for or _stable_port(paths[0], f"files:{len(paths)}"),
            _files_title(list(paths)),
            open_browser=ctx.obj["open_browser"],
            may_fall_back=not asked_for,
        )
    )


@main.command("transcript")
@click.argument("path", required=True, type=click.Path(exists=True, path_type=Path))
@click.pass_context
def transcript_cmd(ctx: click.Context, path: Path) -> None:
    """Review a conversation transcript JSONL file."""
    log.info("loading_transcript", path=str(path))
    diff_files = TranscriptService().parse(path)
    if not diff_files:
        sys.stderr.write("No messages to review.\n")
        return
    log.info("content_loaded", file_count=len(diff_files), mode=ReviewMode.TRANSCRIPT)
    asked_for = ctx.obj["port"]
    _run_review(
        _serve(
            diff_files,
            ReviewMode.TRANSCRIPT,
            asked_for or _stable_port(path, "transcript"),
            _transcript_title(path),
            open_browser=ctx.obj["open_browser"],
            may_fall_back=not asked_for,
        )
    )

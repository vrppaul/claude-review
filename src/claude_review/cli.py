"""CLI entry point for claude-review."""

import asyncio
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

log = structlog.get_logger()

# How long the review may have no browser attached before the server winds
# down. A reload drops the socket and takes it again within a moment.
DISCONNECT_GRACE = 3.0


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
) -> str:
    """Start the review server and return formatted review markdown."""
    state = ServerState(shutdown_event=asyncio.Event())
    app = create_app(diff_files=diff_files, state=state, mode=mode, title=title, root=root, base=base)

    # Bind before handing the socket to uvicorn: a port clash then surfaces here
    # as an OSError we can explain, instead of uvicorn calling sys.exit() from
    # inside the event loop and printing a traceback.
    sock = _bind(port)
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

    try:
        await asyncio.gather(server.serve(sockets=[sock]), wait_for_shutdown())
    finally:
        sock.close()

    return state.result or ""


def _bind(port: int) -> socket.socket:
    """Take the loopback port the server will listen on.

    Raises:
        PortUnavailableError: If the port is already taken.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("127.0.0.1", port))
    except OSError as e:
        sock.close()
        msg = f"port {port} is already in use — pass a different --port, or omit it to pick a free one"
        raise PortUnavailableError(msg) from e
    sock.listen(128)
    return sock


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
@click.option("--port", default=0, type=int, help="Port to run the server on.")
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
    """Wait for the reader to ask about a comment thread.

    Prints one JSON object and exits, so a caller can loop: a question to
    answer, "timeout" if nothing was asked, or "closed" once the review is
    over. Answer with `claude-review reply`.
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
@click.argument("text", required=True, type=str)
def reply_cmd(port: int, thread: str, text: str) -> None:
    """Answer a question the reader asked about a comment thread."""
    _call(
        f"http://127.0.0.1:{port}/api/reply",
        payload={"thread_id": thread, "text": text},
    )


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
        return await _serve(
            diff_files,
            ReviewMode.DIFF,
            ctx.obj["port"],
            _diff_title(repo_path, base),
            root=root,
            base=base,
            open_browser=ctx.obj["open_browser"],
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
    _run_review(
        _serve(
            diff_files,
            ReviewMode.FILES,
            ctx.obj["port"],
            _files_title(list(paths)),
            open_browser=ctx.obj["open_browser"],
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
    _run_review(
        _serve(
            diff_files,
            ReviewMode.TRANSCRIPT,
            ctx.obj["port"],
            _transcript_title(path),
            open_browser=ctx.obj["open_browser"],
        )
    )

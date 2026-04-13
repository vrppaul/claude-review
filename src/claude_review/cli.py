"""CLI entry point for claude-review."""

import asyncio
import logging
import sys
import webbrowser
from pathlib import Path

import click
import structlog
import uvicorn

from claude_review.domain.models import DiffFile, ReviewMode
from claude_review.presentation.app import create_app
from claude_review.presentation.state import ServerState
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_service import DiffService
from claude_review.services.text_file_service import TextFileService
from claude_review.services.transcript_service import TranscriptService

log = structlog.get_logger()

HEARTBEAT_TIMEOUT = 10.0


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


async def _load_diff(repo_path: Path, base: str | None = None) -> list[DiffFile]:
    """Load diff files from a git repository."""
    git_repo = GitRepository()
    diff_service = DiffService(git_repository=git_repo)
    log.info("loading_diff", path=str(repo_path), base=base)
    return await diff_service.get_diff(repo_path, base=base)


async def _serve(
    diff_files: list[DiffFile],
    mode: ReviewMode,
    port: int,
    *,
    open_browser: bool = True,
) -> str:
    """Start the review server and return formatted review markdown."""
    state = ServerState(shutdown_event=asyncio.Event())
    app = create_app(diff_files=diff_files, state=state, mode=mode)

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
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

        actual_port = server.servers[0].sockets[0].getsockname()[1]
        url = f"http://127.0.0.1:{actual_port}"
        log.info("server_started", url=url)

        if open_browser:
            await asyncio.to_thread(_open_browser, url)

        while not state.shutdown_event.is_set():
            await asyncio.sleep(1.0)
            if state.last_heartbeat is not None:
                now = asyncio.get_running_loop().time()
                if now - state.last_heartbeat > HEARTBEAT_TIMEOUT:
                    log.info("heartbeat_timeout", last_heartbeat_age=round(now - state.last_heartbeat, 1))
                    break

        server.should_exit = True
        log.info("server_shutting_down")

    await asyncio.gather(server.serve(), wait_for_shutdown())

    return state.result or ""


def _open_browser(url: str) -> None:
    webbrowser.open_new(url)


def _print_result(result: str) -> None:
    """Write review result to stdout if non-empty."""
    if result:
        sys.stdout.write(result)
        sys.stdout.write("\n")


@click.group()
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
        diff_files = await _load_diff(repo_path, base=base)
        if not diff_files:
            sys.stderr.write("No changes found.\n")
            return ""
        log.info("content_loaded", file_count=len(diff_files), mode=ReviewMode.DIFF)
        return await _serve(diff_files, ReviewMode.DIFF, ctx.obj["port"], open_browser=ctx.obj["open_browser"])

    _print_result(asyncio.run(_run()))


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
    result = asyncio.run(_serve(diff_files, ReviewMode.FILES, ctx.obj["port"], open_browser=ctx.obj["open_browser"]))
    _print_result(result)


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
    result = asyncio.run(
        _serve(diff_files, ReviewMode.TRANSCRIPT, ctx.obj["port"], open_browser=ctx.obj["open_browser"])
    )
    _print_result(result)

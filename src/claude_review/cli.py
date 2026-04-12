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
from claude_review.presentation.schemas import ServerState
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_service import DiffService
from claude_review.services.text_file_service import TextFileService

log = structlog.get_logger()


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


async def _load_diff(repo_path: Path) -> list[DiffFile]:
    """Load diff files from a git repository."""
    git_repo = GitRepository()
    diff_service = DiffService(git_repository=git_repo)
    log.info("loading_diff", path=str(repo_path))
    return await diff_service.get_diff(repo_path)


def _load_text_files(paths: list[Path]) -> list[DiffFile]:
    """Load text files for review."""
    log.info("loading_files", count=len(paths))
    return TextFileService().read_files(paths)


async def run(
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

    heartbeat_timeout = 10.0  # seconds without heartbeat before shutdown

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
                if now - state.last_heartbeat > heartbeat_timeout:
                    log.info("heartbeat_timeout", last_heartbeat_age=round(now - state.last_heartbeat, 1))
                    break

        server.should_exit = True
        log.info("server_shutting_down")

    await asyncio.gather(server.serve(), wait_for_shutdown())

    return state.result or ""


def _open_browser(url: str) -> None:
    webbrowser.open_new(url)


@click.command()
@click.argument("path", required=False, type=click.Path(exists=True, path_type=Path))
@click.option(
    "--files",
    multiple=True,
    type=click.Path(exists=True, path_type=Path),
    help="Review text files instead of git diff.",
)
@click.option("--port", default=0, type=int, help="Port to run the server on.")
@click.option("--no-open", is_flag=True, help="Don't open the browser automatically.")
@click.option("--verbose", is_flag=True, help="Enable diagnostic logging to stderr.")
def main(path: Path | None, files: tuple[Path, ...], port: int, no_open: bool, verbose: bool) -> None:
    """Browser-based code review tool for Claude Code."""
    if files and path:
        raise click.UsageError("--files and positional path cannot be used together.")

    _configure_logging(verbose=verbose)

    if files:
        diff_files = _load_text_files(list(files))
        mode = ReviewMode.FILES
        no_content_msg = "No content to review.\n"
    else:
        repo_path = (path or Path(".")).resolve()
        diff_files = asyncio.run(_load_diff(repo_path))
        mode = ReviewMode.DIFF
        no_content_msg = "No changes found.\n"

    if not diff_files:
        sys.stderr.write(no_content_msg)
        return

    log.info("content_loaded", file_count=len(diff_files), mode=mode)
    result = asyncio.run(run(diff_files, mode, port, open_browser=not no_open))

    if result:
        sys.stdout.write(result)
        sys.stdout.write("\n")

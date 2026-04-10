"""CLI entry point for claude-review."""

import argparse
import asyncio
import logging
import sys
import webbrowser
from pathlib import Path

import structlog
import uvicorn

from claude_review.presentation.app import create_app
from claude_review.presentation.schemas import ServerState
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_service import DiffService

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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="claude-review",
        description="Browser-based code review tool for Claude Code",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Port to run the server on (default: auto-assign)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Don't open the browser automatically",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable diagnostic logging to stderr",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the git repository (default: current directory)",
    )
    return parser.parse_args(argv)


async def run(repo_path: Path, port: int, *, open_browser: bool = True) -> str:
    """Run the review server and return formatted review markdown."""
    git_repo = GitRepository()
    diff_service = DiffService(git_repository=git_repo)
    log.info("loading_diff", path=str(repo_path))
    diff_files = await diff_service.get_diff(repo_path)

    if not diff_files:
        log.info("no_changes_found")
        return ""

    log.info("diff_loaded", file_count=len(diff_files))

    state = ServerState(shutdown_event=asyncio.Event())
    app = create_app(diff_files=diff_files, state=state)

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
    webbrowser.open(url)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    _configure_logging(verbose=args.verbose)
    repo_path = Path(args.path).resolve()
    result = asyncio.run(run(repo_path, args.port, open_browser=not args.no_open))

    if result:
        sys.stdout.write(result)
        sys.stdout.write("\n")
    else:
        sys.stderr.write("No changes found.\n")

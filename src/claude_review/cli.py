"""CLI entry point for claude-review."""

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

import uvicorn

from claude_review.presentation.app import create_app
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_service import DiffService


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
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
    diff_files = await diff_service.get_diff(repo_path)

    if not diff_files:
        return ""

    shutdown_event = asyncio.Event()
    result_holder: list[str] = []
    heartbeat_holder: list[float] = []
    app = create_app(
        diff_files=diff_files,
        shutdown_event=shutdown_event,
        result_holder=result_holder,
        heartbeat_holder=heartbeat_holder,
    )

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)

    heartbeat_timeout = 10.0  # seconds without heartbeat before shutdown

    async def wait_for_shutdown() -> None:
        for _ in range(100):  # 5 second startup timeout
            if server.started:
                break
            await asyncio.sleep(0.05)
        if not server.started:
            server.should_exit = True
            return

        actual_port = server.servers[0].sockets[0].getsockname()[1]
        url = f"http://127.0.0.1:{actual_port}"

        if open_browser:
            await asyncio.to_thread(_open_browser, url)

        # Wait for either submit or heartbeat timeout (browser closed)
        while not shutdown_event.is_set():
            await asyncio.sleep(1.0)
            if heartbeat_holder:
                last = heartbeat_holder[0]
                now = asyncio.get_event_loop().time()
                if now - last > heartbeat_timeout:
                    break

        server.should_exit = True

    await asyncio.gather(server.serve(), wait_for_shutdown())

    return result_holder[0] if result_holder else ""


def _open_browser(url: str) -> None:
    """Open browser without GTK warnings polluting stdout/stderr."""
    subprocess.Popen(
        ["xdg-open", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    args = parse_args(argv)
    repo_path = Path(args.path).resolve()
    result = asyncio.run(run(repo_path, args.port, open_browser=not args.no_open))

    if result:
        sys.stdout.write(result)
        sys.stdout.write("\n")
    else:
        sys.stderr.write("No changes found.\n")

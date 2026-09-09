"""Tests that run the CLI as a real process.

Click's CliRunner catches SystemExit, which hides exactly the failure this
covers: what the user sees in a terminal when the server cannot start.
"""

import socket
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path

from websockets.sync.client import connect


def _run_cli(*args: str, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "claude_review", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def test_busy_port_reports_one_readable_line(tmp_git_repo: Path) -> None:
    """A taken port produces an explanation, not a traceback."""
    holder = socket.socket()
    holder.bind(("127.0.0.1", 0))
    holder.listen(1)
    taken_port = holder.getsockname()[1]

    try:
        (tmp_git_repo / "initial.txt").write_text("changed\n")
        result = _run_cli("--port", str(taken_port), "--no-open", "diff", str(tmp_git_repo))
    finally:
        holder.close()

    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert str(taken_port) in result.stderr
    assert "already in use" in result.stderr


def test_version_is_reported() -> None:
    """--version prints the installed version."""
    result = _run_cli("--version")

    assert result.returncode == 0
    assert version("claude-review") in result.stdout


def test_the_session_socket_is_served_by_the_real_server(tmp_git_repo: Path) -> None:
    """Starlette's test client implements sockets itself, so it cannot catch a
    server that was built without websocket support. This runs the real one."""
    (tmp_git_repo / "initial.txt").write_text("changed\n")
    port = _free_port()

    server = subprocess.Popen(
        [sys.executable, "-m", "claude_review", "--port", str(port), "--no-open", "diff", str(tmp_git_repo)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_server(port)
        with connect(f"ws://127.0.0.1:{port}/api/session") as socket:
            assert socket.protocol.state.name == "OPEN"
    finally:
        server.kill()
        server.wait(timeout=10)


def test_the_server_winds_down_once_the_review_is_closed(tmp_git_repo: Path) -> None:
    """Closing the tab ends the session; the CLI must not hang waiting."""
    (tmp_git_repo / "initial.txt").write_text("changed\n")
    port = _free_port()

    server = subprocess.Popen(
        [sys.executable, "-m", "claude_review", "--port", str(port), "--no-open", "diff", str(tmp_git_repo)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_server(port)
        with connect(f"ws://127.0.0.1:{port}/api/session"):
            pass

        server.wait(timeout=20)
        assert server.returncode == 0
    finally:
        if server.poll() is None:
            server.kill()


def test_a_reload_does_not_end_the_session(tmp_git_repo: Path) -> None:
    """A reload drops the socket and takes it again a moment later."""
    (tmp_git_repo / "initial.txt").write_text("changed\n")
    port = _free_port()

    server = subprocess.Popen(
        [sys.executable, "-m", "claude_review", "--port", str(port), "--no-open", "diff", str(tmp_git_repo)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_server(port)
        with connect(f"ws://127.0.0.1:{port}/api/session"):
            pass
        time.sleep(0.5)
        with connect(f"ws://127.0.0.1:{port}/api/session"):
            time.sleep(5)
            assert server.poll() is None, "the server gave up on a reloaded review"
    finally:
        if server.poll() is None:
            server.kill()
            server.wait(timeout=10)


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _wait_for_server(port: int, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    raise AssertionError(f"server did not come up on port {port}")

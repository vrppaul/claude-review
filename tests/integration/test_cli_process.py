"""Tests that run the CLI as a real process.

Click's CliRunner catches SystemExit, which hides exactly the failure this
covers: what the user sees in a terminal when the server cannot start.
"""

import socket
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path


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

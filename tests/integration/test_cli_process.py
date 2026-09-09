"""Tests that run the CLI as a real process.

Click's CliRunner catches SystemExit, which hides exactly the failure this
covers: what the user sees in a terminal when the server cannot start.
"""

import json
import socket
import subprocess
import sys
import time
import urllib.request
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


def _next_push(socket, kind: str, tries: int = 5) -> dict:
    """Read pushes until the one being waited for arrives.

    The socket carries more than answers — a review is told when an agent
    attaches, and when a round retakes the diff.
    """
    for _ in range(tries):
        message = json.loads(socket.recv(timeout=10))
        if message.get("type") == kind:
            return message
    msg = f"no {kind} push arrived"
    raise AssertionError(msg)


def test_a_question_and_its_answer_travel_between_processes(tmp_git_repo: Path) -> None:
    """The reader asks in one process; the answer is written in another."""
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

        # A browser holds the review open and hears the answer come back
        with connect(f"ws://127.0.0.1:{port}/api/session") as review:
            waiting = subprocess.Popen(
                [sys.executable, "-m", "claude_review", "wait", "--port", str(port), "--seconds", "20"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(1.0)

            _post(
                port,
                "/api/ask",
                {
                    "thread_id": "comment-1",
                    "question_id": "comment-1",
                    "file": "initial.txt",
                    "side": "new",
                    "start_line": 1,
                    "end_line": 1,
                    "quote": ["changed"],
                    "body": "Why this rather than the constant?",
                },
            )

            asked = json.loads(waiting.communicate(timeout=30)[0])
            assert asked["type"] == "question"
            assert asked["question"]["body"] == "Why this rather than the constant?"

            answer = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "claude_review",
                    "reply",
                    "--port",
                    str(port),
                    "--thread",
                    "comment-1",
                    "--question",
                    "comment-1",
                    "Because the constant moved to config",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            assert answer.returncode == 0

            assert _next_push(review, "reply") == {
                "type": "reply",
                "thread_id": "comment-1",
                "question_id": "comment-1",
                "text": "Because the constant moved to config",
            }
    finally:
        server.kill()
        server.wait(timeout=10)


def test_waiting_reports_when_nothing_was_asked(tmp_git_repo: Path) -> None:
    """A caller in a loop needs to be told, not left hanging."""
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
        result = _run_cli("wait", "--port", str(port), "--seconds", "1")

        assert json.loads(result.stdout)["type"] == "timeout"
    finally:
        server.kill()
        server.wait(timeout=10)


def _post(port: int, path: str, payload: dict) -> None:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        response.read()


def test_expanding_context_works_from_a_subdirectory(tmp_git_repo: Path) -> None:
    """Git reports paths from the repository root, whatever directory it ran in."""
    nested = tmp_git_repo / "sub"
    nested.mkdir()
    (nested / "app.py").write_text("".join(f"line {i}\n" for i in range(1, 41)))
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add"], cwd=tmp_git_repo, check=True, capture_output=True)
    (nested / "app.py").write_text("".join(f"line {i}\n" for i in range(1, 40)) + "changed\n")
    port = _free_port()

    server = subprocess.Popen(
        [sys.executable, "-m", "claude_review", "--port", str(port), "--no-open", "diff"],
        cwd=nested,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_server(port)
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/file-window?path=sub/app.py&start=1&end=3",
            headers={"Host": f"127.0.0.1:{port}"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            window = json.loads(response.read())

        assert window["lines"] == ["line 1", "line 2", "line 3"]
    finally:
        server.kill()
        server.wait(timeout=10)


def test_the_url_is_printed_when_no_browser_is_opened(tmp_git_repo: Path) -> None:
    """Otherwise there is nothing on screen saying where the review is."""
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
        time.sleep(0.5)
        server.kill()
        _, stderr = server.communicate(timeout=10)

        assert f"http://127.0.0.1:{port}" in stderr
    finally:
        if server.poll() is None:
            server.kill()


def test_waiting_on_a_server_that_is_not_there_explains_itself(tmp_path: Path) -> None:
    """These commands run in a loop, where a traceback says nothing useful."""
    result = _run_cli("wait", "--port", str(_free_port()), "--seconds", "1")

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "no review is listening" in result.stderr


def test_replying_to_a_thread_that_is_refused_explains_itself(tmp_git_repo: Path) -> None:
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
        result = _run_cli("reply", "--port", str(port), "--thread", "x" * 500, "hello")

        assert result.returncode != 0
        assert "Traceback" not in result.stderr
        assert "refused" in result.stderr
    finally:
        server.kill()
        server.wait(timeout=10)

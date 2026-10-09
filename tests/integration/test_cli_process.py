"""Tests that run the CLI as a real process.

Click's CliRunner catches SystemExit, which hides exactly the failure this
covers: what the user sees in a terminal when the server cannot start. And
only the process can end: whether a closed tab winds the review down is a
question about it, not about the app it serves.
"""

import json
import os
import queue
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from collections.abc import Callable, Iterator, Mapping
from importlib.metadata import version
from pathlib import Path
from typing import IO

import pytest
from websockets.exceptions import InvalidStatus
from websockets.sync.client import ClientConnection, connect
from websockets.typing import Origin

from claude_review.cli import DISCONNECT_GRACE
from claude_review.domain.models import CommentSeverity
from claude_review.presentation.schemas import PushKind
from tests.helpers import ANY_PORT, FIRST_THREAD_ID, LOOPBACK, git, line_on_the_wire, thread_on_the_wire

# The command line, as the user runs it, from the interpreter running the tests
COMMAND_LINE = [sys.executable, "-m", "claude_review"]
# How the review says where it is, on stderr, once it is serving
ADDRESS_PREFIX = "Review ready at "
# How long a review process has to start and say where it is
STARTUP_SECONDS = 20.0
# How long any one command, or a review asked to end, has to finish
COMMAND_SECONDS = 30.0
# How long a push takes to arrive over the socket, at most
PUSH_SECONDS = 10.0
# Enough reads to get past the pushes a test is not about
PUSHES_READ = 5

# A reload drops the socket and takes it again within a moment
MOMENTS_PER_GRACE = 10
RELOAD_SECONDS = DISCONNECT_GRACE / MOMENTS_PER_GRACE
# More than the review takes to look again once the grace has run out
NOTICE_SECONDS = 1.0
PAST_GRACE_SECONDS = DISCONNECT_GRACE + NOTICE_SECONDS

# How long the agent's own wait lasts, in the commands these tests run: long
# enough for what the test sets going, briefly when nothing will come, and
# far longer than anything that should end it sooner
AGENT_WAIT_SECONDS = "20"
BRIEF_WAIT_SECONDS = "1"
LONG_WAIT_SECONDS = "120"
# A port for a command that refuses before it calls anything
NEVER_CALLED_PORT = "1"
# Longer than any thread id the review accepts
OVERLONG_THREAD_ID = "x" * 500
# What a machine with no browser to open looks like
NO_BROWSER = {"BROWSER": "/bin/false", "DISPLAY": "", "WAYLAND_DISPLAY": ""}
# A page on somebody else's site
FOREIGN_ORIGIN = Origin("https://attacker.example")


class CliProcess:
    """The command line running as a process of its own, its output read as it is written.

    Read on threads of their own, so that a test waiting for a line has a
    deadline, and so that a chatty process never stalls on a full pipe.
    """

    def __init__(self, arguments: list[str], *, cwd: Path | None, environment: dict[str, str]) -> None:
        self._process = subprocess.Popen(
            [*COMMAND_LINE, *arguments],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            env=environment,
        )
        self._printed: list[str] = []
        self._said: queue.Queue[str] = queue.Queue()
        assert self._process.stdout is not None
        assert self._process.stderr is not None
        self._readers = [
            threading.Thread(target=_collect, args=(self._process.stdout, self._printed.append), daemon=True),
            threading.Thread(target=_collect, args=(self._process.stderr, self._said.put), daemon=True),
        ]
        for reader in self._readers:
            reader.start()

    def wait_for_address(self) -> str:
        """The address the review says it is ready at, once it says it."""
        deadline = time.monotonic() + STARTUP_SECONDS
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                line = self._said.get(timeout=remaining)
            except queue.Empty:
                break
            if line.startswith(ADDRESS_PREFIX):
                return line.removeprefix(ADDRESS_PREFIX).strip()
        failure = f"the review never said where it was within {STARTUP_SECONDS} seconds"
        raise AssertionError(failure)

    def outlives(self, seconds: float) -> bool:
        """Whether the process is still running once the time is up."""
        try:
            self._process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            return True
        return False

    def finish(self) -> int:
        """Wait for the process to end on its own, and say how it ended."""
        return self._process.wait(timeout=COMMAND_SECONDS)

    def printed(self) -> str:
        """Everything written to stdout, once the process has ended."""
        self.finish()
        for reader in self._readers:
            reader.join(timeout=COMMAND_SECONDS)
        return "".join(self._printed)

    def terminate(self) -> None:
        """Stop it the way `kill` does."""
        self._process.terminate()

    def stop(self) -> None:
        """Kill it if it is still running, and reap it either way."""
        if self._process.poll() is None:
            self._process.kill()
        self._process.wait(timeout=COMMAND_SECONDS)


def _collect(stream: IO[str], keep: Callable[[str], None]) -> None:
    """Hand on every line a stream carries until it closes."""
    for line in stream:
        keep(line)


class CliProcesses:
    """Runs the command line as the user would, and leaves nothing running after the test.

    Every process starts with the reader's files kept under the test's own
    directory, so no test reads or writes the real ones.
    """

    def __init__(self, environment: dict[str, str]) -> None:
        self._environment = environment
        self._started: list[CliProcess] = []

    def start(
        self, *arguments: str, cwd: Path | None = None, environment: Mapping[str, str] | None = None
    ) -> CliProcess:
        """Start a command, with whatever the test changes in its environment on top of the harness's."""
        started = CliProcess(list(arguments), cwd=cwd, environment={**self._environment, **(environment or {})})
        self._started.append(started)
        return started

    def review(self, repo: Path, port: int) -> CliProcess:
        """A review of the repository's uncommitted changes, served and ready."""
        started = self.start("--port", str(port), "--no-open", "diff", str(repo))
        started.wait_for_address()
        return started

    def run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        """Run a command to the end, as an agent does between reads."""
        return subprocess.run(
            [*COMMAND_LINE, *arguments],
            capture_output=True,
            text=True,
            timeout=COMMAND_SECONDS,
            check=False,
            env=self._environment,
        )

    def stop_all(self) -> None:
        for started in self._started:
            started.stop()


@pytest.fixture
def cli(tmp_path_factory: pytest.TempPathFactory) -> Iterator[CliProcesses]:
    """The command line, run with the reader's files under this test's own directory."""
    reader_home = tmp_path_factory.mktemp("reader")
    environment = {
        **os.environ,
        "XDG_CONFIG_HOME": str(reader_home / "config"),
        "XDG_STATE_HOME": str(reader_home / "state"),
    }
    processes = CliProcesses(environment)
    yield processes
    processes.stop_all()


@pytest.fixture
def changed_repo(tmp_git_repo: Path) -> Path:
    """A repository with something to review."""
    (tmp_git_repo / "initial.txt").write_text("changed\n")
    return tmp_git_repo


@pytest.fixture
def port() -> int:
    """A port nothing is listening on."""
    with socket.socket() as probe:
        probe.bind((LOOPBACK, ANY_PORT))
        return probe.getsockname()[1]


def _session(port: int) -> ClientConnection:
    """The session socket, held open as a review on screen holds it; with no Origin, as from no page at all."""
    return connect(f"ws://{LOOPBACK}:{port}/api/session")


def _next_push(review_socket: ClientConnection, kind: PushKind) -> dict:
    """Read pushes until the one being waited for arrives.

    The socket carries more than any one test is about — a review is told
    when an agent attaches, and when a round retakes the diff.
    """
    for _ in range(PUSHES_READ):
        message = json.loads(review_socket.recv(timeout=PUSH_SECONDS))
        if message.get("type") == kind:
            return message
    failure = f"no {kind} push arrived"
    raise AssertionError(failure)


def _post(port: int, path: str, payload: dict) -> None:
    request = urllib.request.Request(
        f"http://{LOOPBACK}:{port}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=COMMAND_SECONDS) as response:
        response.read()


def test_busy_port_reports_one_readable_line(changed_repo: Path, cli: CliProcesses) -> None:
    """A taken port produces an explanation, not a traceback."""
    with socket.socket() as holder:
        holder.bind((LOOPBACK, ANY_PORT))
        holder.listen()
        taken_port = holder.getsockname()[1]

        result = cli.run("--port", str(taken_port), "--no-open", "diff", str(changed_repo))

    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert str(taken_port) in result.stderr
    assert "already in use" in result.stderr


def test_version_is_reported(cli: CliProcesses) -> None:
    """--version prints the installed version."""
    result = cli.run("--version")

    assert result.returncode == 0
    assert version("claude-review") in result.stdout


@pytest.mark.parametrize("opening", [["--no-open"], []], ids=["told-not-to-open", "opening-a-browser"])
def test_the_address_is_printed_whether_or_not_a_browser_opens(
    changed_repo: Path, cli: CliProcesses, port: int, opening: list[str]
) -> None:
    """Opening a window and saying where the review is are two different jobs.

    Said only in the "do not open" branch, the address was unreachable to
    anything that started the review for somebody else — so every agent
    passed `--no-open` to get it, and nobody's browser ever opened. On a
    machine with no browser to find, it is all there is to go on.
    """
    review = cli.start("--port", str(port), *opening, "diff", str(changed_repo), environment=NO_BROWSER)

    assert review.wait_for_address() == f"http://{LOOPBACK}:{port}"


def test_the_session_socket_is_served_by_the_real_server(changed_repo: Path, cli: CliProcesses, port: int) -> None:
    """Starlette's test client implements sockets itself, so it cannot catch a
    server that was built without websocket support. This runs the real one."""
    cli.review(changed_repo, port)

    with _session(port) as review_socket:
        assert review_socket.protocol.state.name == "OPEN"


def test_the_server_winds_down_once_the_review_is_closed(changed_repo: Path, cli: CliProcesses, port: int) -> None:
    """Closing the tab ends the session; the CLI must not hang waiting."""
    review = cli.review(changed_repo, port)

    with _session(port):
        pass

    assert review.finish() == 0


def test_a_reload_does_not_end_the_session(changed_repo: Path, cli: CliProcesses, port: int) -> None:
    """A reload drops the socket and takes it again a moment later."""
    review = cli.review(changed_repo, port)

    with _session(port):
        pass
    time.sleep(RELOAD_SECONDS)
    with _session(port):
        assert review.outlives(PAST_GRACE_SECONDS), "the server gave up on a reloaded review"


def test_a_review_nobody_has_opened_is_not_ended_by_a_page_it_refused(
    changed_repo: Path, cli: CliProcesses, port: int
) -> None:
    """Starting without a browser is normal, and a refused handshake is not a reader leaving."""
    review = cli.review(changed_repo, port)

    with pytest.raises(InvalidStatus), connect(f"ws://{LOOPBACK}:{port}/api/session", origin=FOREIGN_ORIGIN):
        pass

    assert review.outlives(PAST_GRACE_SECONDS), "the review ended without ever being opened"


def test_a_question_and_its_answer_travel_between_processes(changed_repo: Path, cli: CliProcesses, port: int) -> None:
    """The reader asks in one process; the answer is written in another."""
    cli.review(changed_repo, port)

    # A browser holds the review open and hears the answer come back
    with _session(port) as review_socket:
        waiting = cli.start("wait", "--port", str(port), "--seconds", AGENT_WAIT_SECONDS)
        # Said to the review the moment the agent starts waiting on it
        _next_push(review_socket, PushKind.ANSWERER)

        _post(
            port,
            "/api/ask",
            {
                "question_id": FIRST_THREAD_ID,
                "thread": thread_on_the_wire(
                    {**line_on_the_wire("initial.txt", 1), "quote": ["changed"]},
                    "Why this rather than the constant?",
                    severity=CommentSeverity.QUESTION,
                ),
            },
        )

        asked = json.loads(waiting.printed())
        assert asked["type"] == "question"
        assert asked["question"]["body"] == "Why this rather than the constant?"

        answer = cli.run(
            "reply",
            "--port",
            str(port),
            "--thread",
            FIRST_THREAD_ID,
            "--question",
            FIRST_THREAD_ID,
            "Because the constant moved to config",
        )
        assert answer.returncode == 0

        assert _next_push(review_socket, PushKind.REPLY) == {
            "type": "reply",
            "thread_id": FIRST_THREAD_ID,
            "question_id": FIRST_THREAD_ID,
            "body": "Because the constant moved to config",
        }


def test_a_panel_message_and_its_answer_travel_between_processes(
    changed_repo: Path, cli: CliProcesses, port: int
) -> None:
    """The panel reaches the same agent the threads do, over the same queue."""
    cli.review(changed_repo, port)

    with _session(port) as review_socket:
        waiting = cli.start("wait", "--port", str(port), "--seconds", AGENT_WAIT_SECONDS)
        _next_push(review_socket, PushKind.ANSWERER)

        _post(port, "/api/message", {"message_id": "panel-1", "body": "Run the tests and say what fails."})

        handed = json.loads(waiting.printed())
        assert handed["type"] == "message"
        assert handed["message"]["body"] == "Run the tests and say what fails."

        answer = cli.run("say", "--port", str(port), "--message", "panel-1", "One failed; fixed and green.")
        assert answer.returncode == 0

        assert _next_push(review_socket, PushKind.CHAT) == {
            "type": "chat",
            "message_id": "panel-1",
            "body": "One failed; fixed and green.",
            "files": [],
        }


def test_the_agent_reports_what_the_review_cannot_measure(changed_repo: Path, cli: CliProcesses, port: int) -> None:
    """Which model, and how much context is left, come from the agent alone."""
    cli.review(changed_repo, port)

    with _session(port) as review_socket:
        reported = cli.run("status", "--port", str(port), "--model", "opus-5", "--context", "53% of 1M")
        assert reported.returncode == 0

        pushed = _next_push(review_socket, PushKind.STATUS)
        assert (pushed["agent"]["model"], pushed["agent"]["context"]) == ("opus-5", "53% of 1M")


def test_the_agent_raises_a_thread_on_a_line_from_its_own_process(
    changed_repo: Path, cli: CliProcesses, port: int
) -> None:
    """What belongs on the code goes on the code, from the command the agent runs."""
    cli.review(changed_repo, port)

    with _session(port) as review_socket:
        raised = cli.run("point", "--port", str(port), "--file", "initial.txt", "--lines", "1", "Kept it on purpose")
        assert raised.returncode == 0

        pushed = _next_push(review_socket, PushKind.POINT)
        assert (pushed["anchor"]["file"], pushed["anchor"]["start_line"]) == ("initial.txt", 1)
        assert pushed["body"] == "Kept it on purpose"


def test_a_file_changed_under_the_review_is_said_to_the_review_on_screen(
    changed_repo: Path, cli: CliProcesses, port: int
) -> None:
    """Said, never acted on: the reader decides when to take the diff again."""
    cli.review(changed_repo, port)

    with _session(port) as review_socket:
        (changed_repo / "initial.txt").write_text("changed again, by somebody else\n")

        assert _next_push(review_socket, PushKind.CHANGED) == {"type": "changed", "moved_count": 1}


def test_reporting_nothing_is_refused_rather_than_sent(cli: CliProcesses) -> None:
    """An empty report would tell the panel to show blanks it already shows."""
    result = cli.run("status", "--port", NEVER_CALLED_PORT)

    assert result.returncode != 0
    assert "nothing to report" in result.stderr


def test_waiting_reports_when_nothing_was_asked(changed_repo: Path, cli: CliProcesses, port: int) -> None:
    """A caller in a loop needs to be told, not left hanging."""
    cli.review(changed_repo, port)

    result = cli.run("wait", "--port", str(port), "--seconds", BRIEF_WAIT_SECONDS)

    assert json.loads(result.stdout)["type"] == "timeout"


def test_expanding_context_works_from_a_subdirectory(tmp_git_repo: Path, cli: CliProcesses, port: int) -> None:
    """Git reports paths from the repository root, whatever directory it ran in."""
    nested = tmp_git_repo / "sub"
    nested.mkdir()
    (nested / "app.py").write_text("".join(f"line {line_number}\n" for line_number in range(1, 41)))
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "add")
    (nested / "app.py").write_text("".join(f"line {line_number}\n" for line_number in range(1, 40)) + "changed\n")

    cli.start("--port", str(port), "--no-open", "diff", cwd=nested).wait_for_address()
    request = urllib.request.Request(f"http://{LOOPBACK}:{port}/api/file-window?path=sub/app.py&start=1&end=3")
    with urllib.request.urlopen(request, timeout=COMMAND_SECONDS) as response:
        window = json.loads(response.read())

    assert window["lines"] == ["line 1", "line 2", "line 3"]


def test_waiting_on_a_server_that_is_not_there_explains_itself(cli: CliProcesses, port: int) -> None:
    """These commands run in a loop, where a traceback says nothing useful."""
    result = cli.run("wait", "--port", str(port), "--seconds", BRIEF_WAIT_SECONDS)

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "no review is listening" in result.stderr


def test_replying_to_a_thread_that_is_refused_explains_itself(changed_repo: Path, cli: CliProcesses, port: int) -> None:
    cli.review(changed_repo, port)

    result = cli.run("reply", "--port", str(port), "--thread", OVERLONG_THREAD_ID, "hello")

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "refused" in result.stderr


def test_an_agent_waiting_when_the_reader_closes_the_review_hears_it_closed(
    changed_repo: Path, cli: CliProcesses, port: int
) -> None:
    """Closing the tab ends the review for the agent too, at once, not when its wait runs out."""
    review = cli.review(changed_repo, port)
    waiting = cli.start("wait", "--port", str(port), "--seconds", LONG_WAIT_SECONDS)

    with _session(port):
        pass

    assert json.loads(waiting.printed())["type"] == "closed"
    assert review.finish() == 0


def test_what_the_agent_never_took_is_written_out_when_the_review_ends(
    changed_repo: Path, cli: CliProcesses, port: int
) -> None:
    """The process stops a moment after the last send; a message still waiting must not go with it."""
    review = cli.review(changed_repo, port)

    _post(port, "/api/message", {"message_id": "panel-1", "body": "Also check the docs."})
    _post(port, "/api/submit", {"threads": [], "body": "Rename the helper.", "end": True})
    printed = review.printed()

    assert "Rename the helper." in printed
    assert "Also check the docs." in printed


def test_a_review_stopped_by_a_signal_cleans_up_and_hands_over_the_last_round(
    changed_repo: Path, cli: CliProcesses, port: int, tmp_path: Path
) -> None:
    """`kill` is how a detached review is stopped; it must not skip the way out."""
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    review = cli.start(
        "--port", str(port), "--no-open", "diff", str(changed_repo), environment={"TMPDIR": str(temporary)}
    )
    review.wait_for_address()

    _post(port, "/api/submit", {"threads": [], "body": "Rename the helper.", "end": False})
    review.terminate()

    assert "Rename the helper." in review.printed()
    assert not list(temporary.glob("*.claude-review-objects"))

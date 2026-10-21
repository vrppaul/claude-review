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
from http import HTTPStatus
from pathlib import Path
from typing import IO
from urllib.parse import urlencode

import pytest

from claude_review.cli.launch_commands import NOTHING_TO_REVIEW
from claude_review.domain.models import CommentSeverity, ReviewMode
from claude_review.presentation.schemas.pushes import (
    AnswererPush,
    ReplyPush,
)
from claude_review.presentation.schemas.session import Welcome
from claude_review.services.review.browser_presence import RELOAD_GRACE_SECONDS
from tests.helpers import (
    ANY_PORT,
    FIRST_THREAD_ID,
    LOOPBACK,
    PNG,
    SESSION_ID,
    SESSION_ROUTE,
    git,
    line_json,
    message_said,
    next_push,
    thread_json,
)
from tests.page_socket import HandshakeRefusedError, PageSocket

# The command line, as the user runs it, from the interpreter running the tests
COMMAND_LINE = [sys.executable, "-m", "claude_review"]
# How the review says where it is, on stderr, once it is serving
ADDRESS_PREFIX = "Review ready at "
# How long a review process has to start and say where it is
STARTUP_SECONDS = 20.0
# How long any one command, or a review asked to end, has to finish
COMMAND_SECONDS = 30.0
# How long what a page says takes to reach the review, read through the agent's commands, at most
HEARD_SECONDS = 10.0

# A reload drops the socket and takes it again within a moment
MOMENTS_PER_GRACE = 10
RELOAD_SECONDS = RELOAD_GRACE_SECONDS / MOMENTS_PER_GRACE
# More than the review takes to look again once the grace has run out
NOTICE_SECONDS = 1.0
PAST_GRACE_SECONDS = RELOAD_GRACE_SECONDS + NOTICE_SECONDS

# How long the agent's own wait lasts, in the commands these tests run: long enough for what the test sets going
AGENT_WAIT_SECONDS = "20"
# How a failure the command line explains begins, on the one line it takes
ONE_LINE_FAILURE = "Error: "
# A conversation as Claude Code writes one, an entry a line: a question, and its answer
CONVERSATION = [
    {"type": "user", "sessionId": SESSION_ID, "message": {"role": "user", "content": "Can you rename the helper?"}},
    {
        "type": "assistant",
        "sessionId": SESSION_ID,
        "message": {"role": "assistant", "content": [{"type": "text", "text": "Renamed it."}]},
    },
]
# What a machine with no browser to open looks like
NO_BROWSER = {"BROWSER": "/bin/false", "DISPLAY": "", "WAYLAND_DISPLAY": ""}
# A page on somebody else's site
FOREIGN_ORIGIN = "https://attacker.example"
# A review that ran on the port before, and the welcome a page left open on it had from it
ANOTHER_REVIEW = "another-review"
WELCOME_FROM_ANOTHER_REVIEW = Welcome(identity=ANOTHER_REVIEW, instance="another-run", sequence=0, resumed=False)
# What writes "echo pwned" into the clipboard of a terminal that prints it (OSC 52), as a reader may paste it
ESCAPE = "\x1b"
CLIPBOARD_WRITE = f"{ESCAPE}]52;c;ZWNobyBwd25lZA==\x07"
# How a terminal control is shown when printed: written out, as JSON writes one
SHOWN_ESCAPE = "\\u001b"


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
        said = []
        while not self._said.empty():
            said.append(self._said.get_nowait())
        failure = f"the review never said where it was within {STARTUP_SECONDS} seconds; it said: {said}"
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

    def said(self) -> str:
        """Everything written to stderr and not yet read, once the process has ended."""
        self.finish()
        for reader in self._readers:
            reader.join(timeout=COMMAND_SECONDS)
        lines = []
        while not self._said.empty():
            lines.append(self._said.get_nowait())
        return "".join(lines)

    def terminate(self) -> None:
        """Stop it the way `kill` does."""
        self._process.terminate()

    def stop(self) -> None:
        """Stop it the way `kill` does if it is still running, killing it outright only if that fails; reap it."""
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=COMMAND_SECONDS)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process.wait(timeout=COMMAND_SECONDS)


def _collect(stream: IO[str], keep: Callable[[str], None]) -> None:
    """Hand on every line a stream carries until it closes."""
    for line in stream:
        keep(line)


class CliProcesses:
    """Runs the command line as the user would, and leaves nothing running after the test.

    Every process starts with the reader's files and its temporary
    directories under the test's own directory, so no test reads or writes
    the real ones, and none leaves anything in the system's.
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
        started = self.start("diff", str(repo), "--port", str(port), "--no-open")
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
    """The command line, run with the reader's files and the temporary directories under this test's own."""
    reader_home = tmp_path_factory.mktemp("reader")
    environment = {
        **os.environ,
        "XDG_CONFIG_HOME": str(reader_home / "config"),
        "XDG_STATE_HOME": str(reader_home / "state"),
        "TMPDIR": str(tmp_path_factory.mktemp("temporary")),
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


def _session(port: int) -> PageSocket:
    """The session socket, held open as a review on screen holds it; with no Origin, as from no page at all."""
    return PageSocket(port)


def _session_of(port: int, welcome: Welcome) -> PageSocket:
    """The session socket of a page that has read its review: it names the review, the run and the last push it had."""
    named = {"identity": welcome.identity, "instance": welcome.instance, "after": welcome.sequence}
    return PageSocket(port, route=f"{SESSION_ROUTE}?{urlencode(named)}")


def _welcome(page: PageSocket) -> Welcome:
    """The welcome that opens every connection."""
    welcome = message_said(page.receive(timeout=HEARD_SECONDS))
    assert isinstance(welcome, Welcome)
    return welcome


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

        result = cli.run("diff", str(changed_repo), "--port", str(taken_port), "--no-open")

    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert str(taken_port) in result.stderr
    assert "already in use" in result.stderr


def _read(port: int, route: str) -> dict:
    """What a route of the review served on the port answers, read as the page reads it."""
    with urllib.request.urlopen(f"http://{LOOPBACK}:{port}{route}", timeout=COMMAND_SECONDS) as response:
        return json.loads(response.read())


def test_a_repository_with_nothing_changed_is_said_to_have_nothing_and_never_served(
    tmp_git_repo: Path, cli: CliProcesses
) -> None:
    result = cli.run("diff", str(tmp_git_repo), "--no-open")

    assert result.returncode == 0
    assert result.stderr == f"{NOTHING_TO_REVIEW[ReviewMode.DIFF]}\n"


@pytest.mark.parametrize(
    ("command", "what"),
    [("diff", "no-repository"), ("files", "not-text")],
    ids=["a-directory-that-is-no-repository", "a-file-that-is-not-text"],
)
def test_what_cannot_be_reviewed_is_refused_in_one_readable_line(
    tmp_path: Path, cli: CliProcesses, command: str, what: str
) -> None:
    (tmp_path / what).mkdir()
    (tmp_path / what / "image.png").write_bytes(PNG)
    named = tmp_path / what if command == "diff" else tmp_path / what / "image.png"

    result = cli.run(command, str(named), "--no-open")

    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert result.stderr.startswith(ONE_LINE_FAILURE)
    assert result.stderr.count("\n") == 1


def test_verbose_says_what_the_review_does_and_otherwise_nothing_is_said_but_the_outcome(
    tmp_git_repo: Path, cli: CliProcesses
) -> None:
    quiet = cli.run("diff", str(tmp_git_repo), "--no-open")
    verbose = cli.run("--verbose", "diff", str(tmp_git_repo), "--no-open")

    assert "loading_diff" in verbose.stderr
    assert "loading_diff" not in quiet.stderr


def test_a_review_against_a_base_shows_what_changed_since_it(tmp_git_repo: Path, cli: CliProcesses, port: int) -> None:
    """Nothing is left uncommitted: everything on screen came from the base onward."""
    (tmp_git_repo / "since.txt").write_text("committed since the base\n")
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "since")

    cli.start("diff", str(tmp_git_repo), "--base", "HEAD~1", "--port", str(port), "--no-open").wait_for_address()

    assert _read(port, "/api/review")["title"] == f"{tmp_git_repo.name}: changes since HEAD~1"
    assert [changed["path"] for changed in _read(port, "/api/diff")["files"]] == ["since.txt"]


def test_files_are_named_as_typed_from_where_the_command_ran(tmp_path: Path, cli: CliProcesses, port: int) -> None:
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "plan.md").write_text("# Plan\n")
    (tmp_path / "README.md").write_text("# Read me\n")

    cli.start("files", "notes/plan.md", "README.md", "--port", str(port), "--no-open", cwd=tmp_path).wait_for_address()

    assert sorted(read["path"] for read in _read(port, "/api/diff")["files"]) == ["README.md", "notes/plan.md"]


def test_a_conversation_is_reviewed_as_its_messages(tmp_path: Path, cli: CliProcesses, port: int) -> None:
    conversation = tmp_path / "conversation.jsonl"
    conversation.write_text("\n".join(json.dumps(entry) for entry in CONVERSATION))

    cli.start("transcript", str(conversation), "--port", str(port), "--no-open").wait_for_address()

    assert _read(port, "/api/review")["mode"] == ReviewMode.TRANSCRIPT
    assert len(_read(port, "/api/diff")["files"]) == len(CONVERSATION)


def test_a_base_that_names_no_commit_is_refused_in_one_readable_line(changed_repo: Path, cli: CliProcesses) -> None:
    result = cli.run("diff", str(changed_repo), "--base", "no-such-ref", "--no-open")

    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "no-such-ref" in result.stderr


def test_a_failure_said_in_words_the_reader_typed_is_shown_never_obeyed(changed_repo: Path, cli: CliProcesses) -> None:
    """What failed is named in its own words — a base, a file, what git said — and they may hold a terminal's controls."""
    result = cli.run("diff", str(changed_repo), "--base", f"main{CLIPBOARD_WRITE}", "--no-open")

    assert result.returncode == 1
    assert ESCAPE not in result.stderr
    assert SHOWN_ESCAPE in result.stderr


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
    review = cli.start("diff", str(changed_repo), "--port", str(port), *opening, environment=NO_BROWSER)

    assert review.wait_for_address() == f"http://{LOOPBACK}:{port}"


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

    with pytest.raises(HandshakeRefusedError) as refused:
        PageSocket(port, origin=FOREIGN_ORIGIN)

    assert refused.value.status_code == HTTPStatus.FORBIDDEN

    assert review.outlives(PAST_GRACE_SECONDS), "the review ended without ever being opened"


def test_a_review_nobody_has_opened_is_not_ended_by_a_page_left_on_another_review(
    changed_repo: Path, cli: CliProcesses, port: int
) -> None:
    """A tab left on a review that ran on this port before comes back to whichever answers now: it is not its reader.

    It is told whose review answers, and let go; its leaving is nobody leaving.
    """
    review = cli.review(changed_repo, port)

    with _session_of(port, WELCOME_FROM_ANOTHER_REVIEW) as left_open:
        assert _welcome(left_open).identity != ANOTHER_REVIEW
        with pytest.raises(ConnectionError):
            left_open.receive(timeout=HEARD_SECONDS)

    assert review.outlives(PAST_GRACE_SECONDS), "a page of another review ended this one"


def test_the_socket_a_page_holds_once_it_has_read_its_review_holds_the_review_open(
    changed_repo: Path, cli: CliProcesses, port: int
) -> None:
    """The page holds a socket while it reads the review, then one naming the review it read, and lets the first go."""
    review = cli.review(changed_repo, port)

    with _session(port) as reading:
        welcome = _welcome(reading)
        named = _session_of(port, welcome)
    with named:
        assert review.outlives(PAST_GRACE_SECONDS), "the review ended under the page that had read it"


def test_a_question_and_its_answer_travel_between_processes(changed_repo: Path, cli: CliProcesses, port: int) -> None:
    """The reader asks in one process; the answer is written in another."""
    cli.review(changed_repo, port)

    # A browser holds the review open and hears the answer come back
    with _session(port) as review_socket:
        waiting = cli.start("wait", "--port", str(port), "--seconds", AGENT_WAIT_SECONDS)
        # Said to the review the moment the agent starts waiting on it
        next_push(review_socket, AnswererPush)

        _post(
            port,
            "/api/ask",
            {
                "question_id": FIRST_THREAD_ID,
                "thread": thread_json(
                    {**line_json("initial.txt", 1), "quote": ["changed"]},
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

        assert next_push(review_socket, ReplyPush) == ReplyPush(
            thread_id=FIRST_THREAD_ID, question_id=FIRST_THREAD_ID, body="Because the constant moved to config"
        )


def test_what_the_agent_never_took_is_written_out_when_the_review_ends(
    changed_repo: Path, cli: CliProcesses, port: int
) -> None:
    """The process stops a moment after the last send; a message still waiting must not go with it."""
    review = cli.review(changed_repo, port)

    _post(port, "/api/message", {"message_id": "panel-1", "body": "Also check the docs.", "images": []})
    _post(port, "/api/submit", {"threads": [], "body": "Rename the helper.", "end": True})
    printed = review.printed()

    assert "Rename the helper." in printed
    assert "Also check the docs." in printed


def test_what_the_review_prints_as_it_ends_is_shown_never_obeyed(
    changed_repo: Path, cli: CliProcesses, port: int
) -> None:
    """The last round carries what the reader wrote and the code quoted; the terminal reading it must obey neither."""
    review = cli.review(changed_repo, port)

    _post(port, "/api/submit", {"threads": [], "body": f"Rename it {CLIPBOARD_WRITE}", "end": True})
    printed = review.printed()

    assert ESCAPE not in printed
    assert SHOWN_ESCAPE in printed


def test_a_review_stopped_by_a_signal_cleans_up_and_hands_over_the_last_round(
    changed_repo: Path, cli: CliProcesses, port: int, tmp_path: Path
) -> None:
    """`kill` is how a detached review is stopped; it must not skip the way out."""
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    review = cli.start(
        "diff", str(changed_repo), "--port", str(port), "--no-open", environment={"TMPDIR": str(temporary)}
    )
    review.wait_for_address()

    _post(port, "/api/submit", {"threads": [], "body": "Rename the helper.", "end": False})
    review.terminate()

    assert "Rename the helper." in review.printed()
    assert not list(temporary.glob("*.claude-review-objects"))


def test_a_review_stopped_by_a_signal_while_its_page_is_open_exits_without_being_killed(
    changed_repo: Path, cli: CliProcesses, port: int
) -> None:
    """A page holding its socket must not keep the process alive past `kill`, so a restart never needs `kill -9`."""
    review = cli.start("diff", str(changed_repo), "--port", str(port), "--no-open")
    review.wait_for_address()

    with _session(port):
        review.terminate()

        assert review.finish() == 0

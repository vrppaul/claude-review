"""The command line as it is typed: what it offers, and what it refuses before it calls anything."""

import re
import socket
import subprocess
import sys

import pytest
from click.testing import CliRunner, Result

from claude_review.cli.main import main
from claude_review.hosting.address import LOOPBACK
from claude_review.hosting.ports import ANY_FREE_PORT
from claude_review.presentation.wire.base import MAX_ID_LENGTH, MAX_WAIT_SECONDS

# What click exits with when a command is typed wrong, before it runs
USAGE_ERROR = 2
# What a command that ran and failed exits with
FAILED = 1

# Where the help starts listing commands, and a line that names one: indented
# once, where a description too long for its line goes on indented further
COMMANDS_HEADING = "Commands:"
COMMAND_LINE = re.compile(r"^  (\S+)  ")
LAUNCH_COMMANDS = ("diff", "files", "transcript")
AGENT_COMMANDS = ("wait", "reply", "catch-up", "say", "progress", "show", "point", "status", "retake")
LONGER_THAN_ANY_ID = "x" * (MAX_ID_LENGTH + 1)
# Words that say nothing
BLANK = "   "
# Loading an agent's command the way the command line does, and listing every module it brought in
LOAD_AN_AGENTS_COMMAND = (
    "import sys; from claude_review.cli.main import main; main.get_command(None, 'wait'); print(*sys.modules)"
)
# The server and the web framework under it: an agent's command calls a review in another process, and needs neither
WEB_STACK = {"uvicorn", "fastapi", "starlette"}


@pytest.fixture
def unused_port() -> str:
    """A port nothing listens on: any call to it finds no review."""
    with socket.socket() as probe:
        probe.bind((LOOPBACK, ANY_FREE_PORT))
        return str(probe.getsockname()[1])


def _run(*arguments: str) -> Result:
    return CliRunner().invoke(main, list(arguments))


def _failed_in_a_line(result: Result, exit_code: int) -> bool:
    """Whether a command failed the way a command line should: a line said, not a traceback."""
    return result.exit_code == exit_code and isinstance(result.exception, SystemExit)


def _offered_commands(help_text: str) -> set[str]:
    """The commands the help lists under its heading, each at the start of a line of its own."""
    listed = help_text.split(COMMANDS_HEADING, 1)[1]
    return {found.group(1) for line in listed.splitlines() if (found := COMMAND_LINE.match(line))}


def test_every_command_is_offered() -> None:
    """An agent driving a review has to find them without being told."""
    result = _run("--help")

    assert result.exit_code == 0
    assert _offered_commands(result.output) == {*LAUNCH_COMMANDS, *AGENT_COMMANDS}


@pytest.mark.parametrize("command", LAUNCH_COMMANDS)
def test_every_launch_takes_where_to_serve_and_whether_to_open_a_window(command: str) -> None:
    result = _run(command, "--help")

    assert "--port" in result.output
    assert "--no-open" in result.output


def test_a_diff_can_be_taken_against_another_base() -> None:
    assert "--base" in _run("diff", "--help").output


@pytest.mark.parametrize("command", ["files", "transcript"])
def test_a_review_of_files_needs_files_to_review(command: str) -> None:
    assert _run(command).exit_code == USAGE_ERROR


@pytest.mark.parametrize("lines", ["abc", "0", "47-42", "4-x"])
def test_lines_that_are_no_line_are_refused_before_anything_is_called(unused_port: str, lines: str) -> None:
    """A wrong range is the typist's to fix, so it is said as a usage error, naming what was typed."""
    result = _run("point", "--port", unused_port, "--file", "a.py", "--lines", lines, "Kept on purpose")

    assert _failed_in_a_line(result, USAGE_ERROR)
    assert f'"{lines}"' in result.output


def test_reporting_nothing_is_refused_rather_than_sent(unused_port: str) -> None:
    """An empty report would tell the panel to show blanks it already shows."""
    result = _run("status", "--port", unused_port)

    assert _failed_in_a_line(result, USAGE_ERROR)
    assert "nothing to report" in result.output


def test_a_wait_longer_than_the_review_allows_is_refused_before_it_is_asked(unused_port: str) -> None:
    result = _run("wait", "--port", unused_port, "--seconds", str(MAX_WAIT_SECONDS + 1))

    assert _failed_in_a_line(result, USAGE_ERROR)


def test_a_call_to_a_review_that_is_not_there_explains_itself(unused_port: str) -> None:
    """These commands run in a loop, where a traceback says nothing useful."""
    result = _run("wait", "--port", unused_port, "--seconds", "1")

    assert _failed_in_a_line(result, FAILED)
    assert "no review is listening" in result.output


@pytest.mark.parametrize(
    ("arguments", "typed_in"),
    [
        (["reply", "--thread", LONGER_THAN_ANY_ID, "Because"], "--thread"),
        (["catch-up", "--thread", "not an id"], "--thread"),
        (["say", ""], "BODY"),
        (["say", BLANK], "BODY"),
        (["progress", "--did", "", "reading the handler"], "--did"),
        (["point", "--file", "", "--lines", "1", "Kept on purpose"], "--file"),
    ],
    ids=["an-overlong-thread-id", "an-id-with-spaces", "an-empty-body", "a-blank-body", "an-empty-step", "no-file"],
)
def test_a_value_the_review_would_refuse_is_refused_naming_where_it_was_typed(
    unused_port: str, arguments: list[str], typed_in: str
) -> None:
    """The typist's to fix, said for the option or argument they typed, before any request is built."""
    command, *rest = arguments
    result = _run(command, "--port", unused_port, *rest)

    assert _failed_in_a_line(result, USAGE_ERROR)
    assert f"'{typed_in}'" in result.output
    assert "would refuse" in result.output


def test_an_agents_command_does_not_load_the_server_or_its_framework() -> None:
    """It runs many times a minute, and whatever serves the review is in another process."""
    loaded = subprocess.run(
        [sys.executable, "-c", LOAD_AN_AGENTS_COMMAND], capture_output=True, text=True, check=True
    ).stdout.split()

    assert WEB_STACK.isdisjoint(loaded)

"""The command line as it is typed: what it offers, and what it refuses before it calls anything."""

import socket

import pytest
from click.testing import CliRunner, Result

from claude_review.cli.main import main
from claude_review.hosting.address import LOOPBACK
from claude_review.hosting.ports import ANY_FREE_PORT
from claude_review.presentation.schemas import MAX_ID_LENGTH, MAX_WAIT_SECONDS

# What click exits with when a command is typed wrong, before it runs
USAGE_ERROR = 2
# What a command that ran and failed exits with
FAILED = 1

# Where the help starts listing commands, one to a line
COMMANDS_HEADING = "Commands:"
LAUNCH_COMMANDS = ("diff", "files", "transcript")
AGENT_COMMANDS = ("wait", "reply", "context", "say", "progress", "show", "point", "status", "round")
LONGER_THAN_ANY_ID = "x" * (MAX_ID_LENGTH + 1)


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
    """The commands the help lists, one to a line under its heading."""
    listed = help_text.split(COMMANDS_HEADING, 1)[1]
    return {line.split()[0] for line in listed.splitlines() if line.strip()}


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
    ("arguments", "field"),
    [
        (["reply", "--thread", LONGER_THAN_ANY_ID, "Because"], "thread_id"),
        (["say", ""], "body"),
    ],
    ids=["an-overlong-thread-id", "an-empty-body"],
)
def test_a_request_the_review_would_refuse_is_not_sent(unused_port: str, arguments: list[str], field: str) -> None:
    """Said as the typist's to fix, naming the field, rather than as a page of validation errors."""
    command, *rest = arguments
    result = _run(command, "--port", unused_port, *rest)

    assert _failed_in_a_line(result, USAGE_ERROR)
    assert f"would refuse this: {field}:" in result.output

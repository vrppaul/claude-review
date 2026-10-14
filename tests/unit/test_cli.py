"""The command line as it is typed: what it offers, and what it refuses before it calls anything."""

import importlib
import inspect
import json
import pkgutil
from pathlib import Path
import re
import socket
import subprocess
import sys

import click
import pytest
from click.testing import CliRunner, Result

import claude_review
from claude_review.cli.main import main
from claude_review.domain.models import MAX_QUOTE_LINES
from claude_review.domain.story import TEXT_LIMITS, StoryText, TextLimit, ToldFrom
from claude_review.hosting.address import LOOPBACK
from claude_review.hosting.ports import ANY_FREE_PORT
from claude_review.presentation.wire.agent import MAX_PROGRESS_STEPS
from claude_review.presentation.wire.base import MAX_FILES_NAMED, MAX_ID_LENGTH, MAX_WAIT_SECONDS
from claude_review.presentation.wire.story import StoryRequest
from claude_review.services.place_words import NOT_LINES
from claude_review.services.story_checks import document_faults
from tests.stories import as_the_agent_writes, step, story_of, without_field

# What click exits with when a command is typed wrong, before it runs
USAGE_ERROR = 2
# What a command that ran and failed exits with
FAILED = 1

# Where the help starts listing commands, and a line that names one: indented
# once, where a description too long for its line goes on indented further
COMMANDS_HEADING = "Commands:"
COMMAND_LINE = re.compile(r"^  (\S+)  ")
LAUNCH_COMMANDS = ("diff", "files", "transcript")
AGENT_COMMANDS = ("wait", "reply", "catch-up", "say", "progress", "show", "point", "status", "retake", "story")
LONGER_THAN_ANY_ID = "x" * (MAX_ID_LENGTH + 1)
# Words that say nothing
BLANK = "   "
# Loading an agent's command the way the command line does, and listing every module it brought in
LOAD_AN_AGENTS_COMMAND = (
    "import sys; from claude_review.cli.main import main; main.get_command(None, 'wait'); print(*sys.modules)"
)
# The server and the web framework under it: an agent's command calls a review in another process, and needs neither
WEB_STACK = {"uvicorn", "fastapi", "starlette", "wsproto"}
# How a review that is not there is said: the command got past what it was typed with
NO_REVIEW = "no review is listening"
# A JSON document as the help shows one: from the line that opens it to the line that closes it, each set in by two
A_DOCUMENT_SHOWN = re.compile(r"^  \{$.*?^  \}$", re.MULTILINE | re.DOTALL)
# What the least story the help shows is made of, at its top
PARTS_OF_THE_LEAST_STORY = ["title", "told_from", "overview", "chapters"]
# What parts the words of a kind of text in its name, and a pattern for either way the help may part them
BETWEEN_WORDS_OF_A_NAME = "_"
EITHER_WAY_WORDS_ARE_PARTED = "[ _]"
# How JSON writes a part that is left out, a list of nothing and a table of nothing
WRITTEN_FOR_WHAT_IS_LEFT_OUT = ["null", "[]", "{}"]


def _repeated(option: str, count: int, value: str = "") -> list[str]:
    """An option typed `count` times, each with a value of its own unless one value is given for all."""
    return [word for index in range(count) for word in (option, value or f"src/file_{index}.py")]


@pytest.fixture
def unused_port() -> str:
    """A port nothing listens on: any call to it finds no review."""
    with socket.socket() as probe:
        probe.bind((LOOPBACK, ANY_FREE_PORT))
        return str(probe.getsockname()[1])


def _run(*arguments: str, typed: str | bytes | None = None) -> Result:
    return CliRunner().invoke(main, list(arguments), input=typed)


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


@pytest.mark.parametrize("lines", ["abc", "4-x"])
def test_what_names_no_lines_is_refused_in_the_words_the_review_refuses_it_with(unused_port: str, lines: str) -> None:
    """One rule for how lines are written, said one way: by a command as by the review it calls."""
    result = _run("point", "--port", unused_port, "--file", "a.py", "--lines", lines, "Kept on purpose")

    assert NOT_LINES in result.output


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


def test_putting_the_work_line_out_takes_nothing_with_it(unused_port: str) -> None:
    """Said beside --done, anything else would be dropped unseen; the typist is told instead."""
    result = _run("progress", "--port", unused_port, "--done", "--step", "running the tests")

    assert _failed_in_a_line(result, USAGE_ERROR)
    assert "--done" in result.output


def test_an_agents_command_does_not_load_the_server_or_its_framework() -> None:
    """It runs many times a minute, and whatever serves the review is in another process."""
    loaded = subprocess.run(
        [sys.executable, "-c", LOAD_AN_AGENTS_COMMAND], capture_output=True, text=True, check=True
    ).stdout.split()

    assert WEB_STACK.isdisjoint(loaded)


@pytest.mark.parametrize(
    ("arguments", "typed_in"),
    [
        (["say", *_repeated("--file", MAX_FILES_NAMED + 1), "Renamed them all"], "--file"),
        (["progress", *_repeated("--file", MAX_FILES_NAMED + 1), "renaming"], "--file"),
        (["progress", *_repeated("--step", MAX_PROGRESS_STEPS + 1), "checking"], "--step"),
        (["progress", *_repeated("--did", MAX_PROGRESS_STEPS + 1), "checking"], "--did"),
    ],
    ids=["files-said-about", "files-worked-on", "steps-under-way", "steps-done"],
)
def test_more_than_the_review_takes_is_refused_naming_the_option(
    unused_port: str, arguments: list[str], typed_in: str
) -> None:
    """Said as the command is parsed, in a line, rather than as a traceback once the request is built."""
    command, *rest = arguments
    result = _run(command, "--port", unused_port, *rest)

    assert _failed_in_a_line(result, USAGE_ERROR)
    assert f"'{typed_in}'" in result.output


def test_a_value_typed_again_is_one_value_and_counts_once(unused_port: str) -> None:
    """The typist meant it once: repeated past the review's bound, it is still one file, and the call is made."""
    result = _run("say", "--port", unused_port, *_repeated("--file", MAX_FILES_NAMED + 1, "src/a.py"), "Here")

    assert _failed_in_a_line(result, FAILED)
    assert NO_REVIEW in result.output


def test_more_branches_than_the_review_shows_are_refused_naming_both_options(unused_port: str) -> None:
    """Each option within the bound, together past it: the work is drawn with no more branches than that."""
    finished = MAX_PROGRESS_STEPS // 2 + 1
    under_way = MAX_PROGRESS_STEPS - finished + 1
    result = _run(
        "progress",
        "--port",
        unused_port,
        *[word for index in range(finished) for word in ("--did", f"done {index}")],
        *[word for index in range(under_way) for word in ("--step", f"running {index}")],
        "checking",
    )

    assert _failed_in_a_line(result, USAGE_ERROR)
    assert "--did" in result.output
    assert "--step" in result.output
    assert str(MAX_PROGRESS_STEPS) in result.output


def test_a_step_both_done_and_under_way_is_refused(unused_port: str) -> None:
    """Two things said of one branch: whichever the review kept, the reader would be told something untrue."""
    result = _run("progress", "--port", unused_port, "--did", "the tests", "--step", "the tests", "checking")

    assert _failed_in_a_line(result, USAGE_ERROR)
    assert "the tests" in result.output


def test_more_lines_than_a_thread_may_quote_are_refused_before_anything_is_called(unused_port: str) -> None:
    """The review would refuse such a thread; the typist hears why as they type it, naming the option."""
    too_many = f"1-{MAX_QUOTE_LINES + 1}"
    result = _run("point", "--port", unused_port, "--file", "a.py", "--lines", too_many, "All of it")

    assert _failed_in_a_line(result, USAGE_ERROR)
    assert "'--lines'" in result.output
    assert str(MAX_QUOTE_LINES) in result.output


@pytest.mark.parametrize(
    "arguments",
    [["--file", "src/a.py"], ["--message", "panel-1"], [BLANK], []],
    ids=["a-file-alone", "a-message-alone", "blank-words", "nothing"],
)
def test_work_with_nothing_to_show_is_refused_rather_than_taken_for_done(
    unused_port: str, arguments: list[str]
) -> None:
    """Work is shown by its words and its branches; with neither, the line would go away though nobody said done."""
    result = _run("progress", "--port", unused_port, *arguments)

    assert _failed_in_a_line(result, USAGE_ERROR)
    assert "--done" in result.output


@pytest.mark.parametrize(
    "branch", [["--step", "three subagents out"], ["--did", "ran the tests"]], ids=["under-way", "done"]
)
def test_work_shown_by_its_branches_alone_is_sent(unused_port: str, branch: list[str]) -> None:
    """Three subagents out says what is being done without a sentence about it."""
    result = _run("progress", "--port", unused_port, *branch)

    assert _failed_in_a_line(result, FAILED)
    assert NO_REVIEW in result.output


@pytest.mark.parametrize(
    ("piped", "reason"), [("", "would refuse"), (b"\xff\xfe not text", "UTF-8")], ids=["nothing", "not-text"]
)
def test_what_stdin_hands_over_is_read_against_the_reviews_rule(
    unused_port: str, piped: str | bytes, reason: str
) -> None:
    """Text from stdin is the typist's as much as an argument is: a mistake in it is said for the argument."""
    result = _run("say", "--port", unused_port, "-", typed=piped)

    assert _failed_in_a_line(result, USAGE_ERROR)
    assert "'BODY'" in result.output
    assert reason in result.output


def _every_command() -> list[click.Command]:
    """Every command the package defines, whichever module it lives in."""
    modules = [
        importlib.import_module(found.name)
        for found in pkgutil.walk_packages(claude_review.__path__, f"{claude_review.__name__}.")
    ]
    found = {
        id(value): value for module in modules for value in vars(module).values() if isinstance(value, click.Command)
    }
    return list(found.values())


def test_every_command_takes_what_it_is_typed_with_by_name() -> None:
    """Click hands every value over by name, and nothing should call a command with a bare value in its place."""
    by_position = [
        command.name
        for command in _every_command()
        if command.callback is not None
        and any(
            parameter.kind is not inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(command.callback).parameters.values()
        )
    ]

    assert by_position == []


# A story's document as the agent writes one, and what stands for stdin where a file is wanted
A_STORY = as_the_agent_writes(story_of(step("src/app.py", 1, 3)))
FROM_STDIN = "-"
# Documents the review would refuse for their shape, and the field each is refused at
MISSHAPEN_STORIES = [
    ({**A_STORY, "doubts": "Whether it holds."}, "doubts"),
    (without_field(A_STORY, "told_from"), "told_from"),
    ({**A_STORY, "chapters": [{**A_STORY["chapters"][0], "steps": [{"file": "src/app.py", "lines": "all"}]}]}, "lines"),
]


@pytest.mark.parametrize(("document", "field"), MISSHAPEN_STORIES)
def test_a_story_the_review_would_refuse_for_its_shape_is_refused_as_it_is_read(
    unused_port: str, document: dict, field: str
) -> None:
    """Said naming the field, before anything is called: the mistake is in the file, and the typist's to fix."""
    result = _run("story", "--port", unused_port, "--file", FROM_STDIN, typed=json.dumps(document))

    assert _failed_in_a_line(result, USAGE_ERROR)
    assert field in result.output
    assert NO_REVIEW not in result.output


def test_a_story_that_is_not_json_is_refused_as_it_is_read(unused_port: str) -> None:
    result = _run("story", "--port", unused_port, "--file", FROM_STDIN, typed="A story, in my own words.")

    assert _failed_in_a_line(result, USAGE_ERROR)
    assert "JSON" in result.output
    assert NO_REVIEW not in result.output


def test_a_story_file_that_is_not_there_is_said_to_be_missing(unused_port: str, tmp_path: Path) -> None:
    missing = tmp_path / "story.json"

    result = _run("story", "--port", unused_port, "--file", str(missing))

    assert _failed_in_a_line(result, USAGE_ERROR)
    assert str(missing) in result.output


def _documents_in_the_help_of_story() -> list[str]:
    """The documents the help of `story` shows, each from the line that opens it to the line that closes it."""
    return A_DOCUMENT_SHOWN.findall(_run("story", "--help").output)


def _example_in_the_help_of_story() -> str:
    """The first document the help of `story` shows: a story with every part one may have."""
    whole, _ = _documents_in_the_help_of_story()
    return whole


@pytest.mark.parametrize(("kind", "limit"), TEXT_LIMITS.items(), ids=lambda given: str(given))
def test_the_help_of_story_says_how_long_each_kind_of_text_may_be_and_where_the_rest_belongs(
    kind: StoryText, limit: TextLimit
) -> None:
    """An agent told to write a story reads its limits here, before the review refuses a text for its length."""
    said = _run("story", "--help").output
    called = kind.replace(BETWEEN_WORDS_OF_A_NAME, EITHER_WAY_WORDS_ARE_PARTED)

    assert re.search(rf"^\s*{called}\b.*\b{limit.characters}\b.*{re.escape(limit.hint)}$", said, re.MULTILINE)


def test_the_example_in_the_help_of_story_is_a_document_the_review_reads_and_finds_no_fault_in() -> None:
    example = StoryRequest.model_validate_json(_example_in_the_help_of_story())

    assert document_faults(example.in_the_review()) == []


@pytest.mark.parametrize("left_out", WRITTEN_FOR_WHAT_IS_LEFT_OUT)
def test_the_example_in_the_help_of_story_leaves_out_no_part_a_story_may_have(left_out: str) -> None:
    """A part the example does not show is one no agent learns it may write."""
    assert left_out not in _example_in_the_help_of_story()


def test_the_help_of_story_shows_the_least_a_story_may_be_which_the_review_reads_and_finds_no_fault_in() -> None:
    """What the first document has and this one lacks may be left out: an agent learns it by seeing both."""
    _, least = _documents_in_the_help_of_story()

    assert document_faults(StoryRequest.model_validate_json(least).in_the_review()) == []


@pytest.mark.parametrize("part", PARTS_OF_THE_LEAST_STORY)
def test_the_least_story_in_the_help_holds_no_part_that_may_be_left_out(unused_port: str, part: str) -> None:
    """With any one of its parts gone, the review reads no story in it."""
    _, least = _documents_in_the_help_of_story()
    lacking = without_field(json.loads(least), part)

    result = _run("story", "--port", unused_port, "--file", FROM_STDIN, typed=json.dumps(lacking))

    assert _failed_in_a_line(result, USAGE_ERROR)
    assert part in result.output


@pytest.mark.parametrize("told_from", ToldFrom)
def test_the_help_of_story_says_everything_a_story_may_be_told_from(told_from: ToldFrom) -> None:
    said = _run("story", "--help").output

    assert re.search(rf"told_from.*\b{told_from}\b", said)

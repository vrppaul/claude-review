"""The agent's commands against a review served on a port: what is typed arrives as meant, or fails in a line.

Run in the test's own process, so a test reads what a command sent from the
review itself. The review answers on the test's loop, so each command runs
on a thread of its own, as it would in a process of its own.
"""

import asyncio
import json
import unicodedata
from http import HTTPStatus
from pathlib import Path

import pytest
from click.testing import CliRunner, Result
from httpx import AsyncClient

from claude_review.cli.main import main
from claude_review.presentation.wire.agent import CatchUpResponse, ProgressStep
from claude_review.presentation.wire.content import ReviewResponse
from claude_review.presentation.wire.pushes import PointPush, ReplyPush
from tests.helpers import (
    CATCH_UP_ROUTE,
    FIRST_THREAD_ID,
    REVIEW_ROUTE,
    REVIEWED_FILE,
    ReviewServers,
    RunningReview,
    line_on_the_wire,
    next_push,
    one_line_file,
    opening_of,
    repository_opening,
    thread_on_the_wire,
)
from tests.page_socket import page_socket_held

# What a command that ran and failed exits with
FAILED = 1

# What a reader pasted from a terminal, or a file holds: a clipboard write
# (OSC 52), a screen cleared (CSI), and the same cleared by one C1 control
ESCAPE = "\x1b"
HOSTILE = f"Look {ESCAPE}]52;c;ZWNobyBwd25lZA==\x07 {ESCAPE}[2J \x9b2J"
# Unicode's category for a control character: C0, DEL and C1 alike
CONTROL_CATEGORY = "Cc"
# What a terminal is meant to act on in printed text: a new line, a tab
MEANT = "\n\t"
MESSAGE_ROUTE = "/api/message"
ASK_ROUTE = "/api/ask"

# An answer in Markdown, which the shell would mangle inside double quotes: it
# runs the code spans and empties the price
MARKDOWN = "Renamed `parse_hunk` to `read_hunk`; it costs $5 less — готово.\n\n- one\n- two"
# What stands for stdin where text is wanted
FROM_STDIN = "-"
# A heredoc ends what it hands over with a line break of its own
FROM_A_HEREDOC = f"{MARKDOWN}\n"


@pytest.fixture
async def review(servers: ReviewServers) -> RunningReview:
    """A review of one file with one line in it, served on a port of its own."""
    return await servers.start(opening_of([one_line_file()]))


async def _run(review: RunningReview, command: str, *arguments: str, typed: str | None = None) -> Result:
    """Run one of the agent's commands against the review, as the agent types it, with what it pipes in."""
    return await asyncio.to_thread(
        CliRunner().invoke, main, [command, "--port", str(review.port), *arguments], input=typed
    )


def _controls_in(printed: str) -> list[str]:
    """Every control character a terminal would act on, other than a new line or a tab."""
    return [
        character
        for character in printed
        if unicodedata.category(character) == CONTROL_CATEGORY and character not in MEANT
    ]


async def _facts(review: RunningReview) -> ReviewResponse:
    """What the review says it is and where it stands, as a page opening reads it."""
    async with AsyncClient(base_url=review.url) as page:
        return ReviewResponse.model_validate_json((await page.get(REVIEW_ROUTE)).content)


@pytest.mark.parametrize("command", ["say", "progress"])
async def test_a_file_typed_twice_is_sent_once(review: RunningReview, command: str) -> None:
    """The typist meant one file; the review, which takes each file once, is never sent it twice."""
    result = await _run(review, command, "--file", REVIEWED_FILE, "--file", REVIEWED_FILE, "Renamed it")

    assert result.exit_code == 0, result.output


async def test_the_work_is_shown_with_each_file_and_branch_once(review: RunningReview) -> None:
    await _run(
        review,
        "progress",
        *("--file", REVIEWED_FILE, "--file", REVIEWED_FILE),
        *("--did", "read the handler", "--did", "read the handler"),
        *("--step", "two subagents out", "--step", "two subagents out"),
        "rewriting the handler",
    )

    work = (await _facts(review)).work

    assert work is not None
    assert work.files == [REVIEWED_FILE]
    assert work.steps == [
        ProgressStep(text="read the handler", done=True),
        ProgressStep(text="two subagents out", done=False),
    ]


@pytest.mark.parametrize(
    ("arguments", "named"),
    [
        (["reply", "--thread", "comment-99", "Because"], "comment-99"),
        (["show", "--file", "src/elsewhere.py"], "src/elsewhere.py"),
    ],
    ids=["a-thread", "a-file"],
)
async def test_what_the_review_does_not_hold_fails_in_a_line_naming_it(
    review: RunningReview, arguments: list[str], named: str
) -> None:
    """An answer or a jump to nowhere would vanish on the page, while the agent took it as done."""
    result = await _run(review, *arguments)

    assert result.exit_code == FAILED
    assert isinstance(result.exception, SystemExit), "failed with a traceback rather than a line"
    assert named in result.output
    assert str(HTTPStatus.NOT_FOUND.value) in result.output


@pytest.mark.parametrize("command", [["wait", "--seconds", "5"], ["catch-up"]], ids=["handed-over", "caught-up"])
async def test_what_the_reader_wrote_is_printed_to_be_read_never_obeyed(
    review: RunningReview, command: list[str]
) -> None:
    """Pasted from a terminal, it may hold what a terminal acts on: shown, it cannot write the agent's clipboard."""
    async with AsyncClient(base_url=review.url) as page:
        await page.post(MESSAGE_ROUTE, json={"message_id": "panel-1", "body": HOSTILE})

    result = await _run(review, *command)

    assert result.exit_code == 0, result.output
    assert _controls_in(result.output) == []
    assert "\\u001b]52" in result.output


async def test_what_is_handed_over_as_json_says_what_was_written(review: RunningReview) -> None:
    """Made safe for the terminal, it is still the JSON of what the reader wrote."""
    async with AsyncClient(base_url=review.url) as page:
        await page.post(MESSAGE_ROUTE, json={"message_id": "panel-1", "body": HOSTILE})

    result = await _run(review, "wait", "--seconds", "5")

    assert json.loads(result.output)["message"]["body"] == HOSTILE


async def test_a_file_named_with_a_control_is_printed_to_be_read_never_obeyed(
    servers: ReviewServers, tmp_git_repo: Path
) -> None:
    """A name is the repository's to choose, and the diff taken again prints the names that changed."""
    named = "clear\x9b2J.py"
    review = await servers.start(await repository_opening(tmp_git_repo))
    (tmp_git_repo / named).write_text("print()\n")

    result = await _run(review, "retake")

    assert result.exit_code == 0, result.output
    assert _controls_in(result.output) == []
    assert json.loads(result.output)["changes"]["paths"] == [named]


async def test_what_is_said_can_come_from_stdin_as_written(review: RunningReview) -> None:
    """A quoted heredoc hands Markdown over untouched, where double quotes would run its code spans."""
    result = await _run(review, "say", FROM_STDIN, typed=FROM_A_HEREDOC)
    async with AsyncClient(base_url=review.url) as page:
        seen = CatchUpResponse.model_validate_json((await page.get(CATCH_UP_ROUTE)).content)

    assert result.exit_code == 0, result.output
    assert [entry.body for entry in seen.panel] == [MARKDOWN]


async def test_the_work_can_come_from_stdin_as_written(review: RunningReview) -> None:
    result = await _run(review, "progress", FROM_STDIN, typed=FROM_A_HEREDOC)
    work = (await _facts(review)).work

    assert result.exit_code == 0, result.output
    assert work is not None
    assert work.text == MARKDOWN


async def test_an_answer_can_come_from_stdin_as_written(review: RunningReview) -> None:
    asked = {"question_id": FIRST_THREAD_ID, "thread": thread_on_the_wire(line_on_the_wire(REVIEWED_FILE, 1), "Why?")}
    async with AsyncClient(base_url=review.url) as reader, page_socket_held(review.port) as page:
        await reader.post(ASK_ROUTE, json=asked)
        result = await _run(review, "reply", "--thread", FIRST_THREAD_ID, FROM_STDIN, typed=FROM_A_HEREDOC)
        answered = await asyncio.to_thread(next_push, page, ReplyPush)

    assert result.exit_code == 0, result.output
    assert answered.body == MARKDOWN


async def test_a_thread_raised_can_say_what_it_says_from_stdin_as_written(review: RunningReview) -> None:
    async with page_socket_held(review.port) as page:
        result = await _run(review, "point", "--file", REVIEWED_FILE, "--lines", "1", FROM_STDIN, typed=FROM_A_HEREDOC)
        raised = await asyncio.to_thread(next_push, page, PointPush)

    assert result.exit_code == 0, result.output
    assert raised.body == MARKDOWN

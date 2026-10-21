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
from httpx import AsyncClient, Client

from claude_review.cli.main import main
from claude_review.domain.models import CommentSeverity, LineSide
from claude_review.presentation.schemas.agent import CatchUpResponse, ProgressStep
from claude_review.presentation.schemas.content import ReviewResponse
from claude_review.presentation.schemas.pushes import ChatPush, PointPush, ProgressPush, ReplyPush, StatusPush
from claude_review.presentation.schemas.story import StoryResponse
from tests.helpers import (
    CATCH_UP_ROUTE,
    FIRST_THREAD_ID,
    REVIEW_ROUTE,
    REVIEWED_FILE,
    REVIEWED_LINE,
    STORY_REQUEST_ROUTE,
    ReviewServers,
    RunningReview,
    added_line,
    diff_file,
    line_json,
    next_push,
    one_line_file,
    removed_line,
    repository_opening,
    thread_json,
    until_the_review_holds_threads,
    work_pushed,
    write_files,
)
from tests.page_socket import page_socket_held
from tests.stories import as_the_agent_writes, planted, step, story_of

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
# A wait that times out almost at once, and long enough after it for it to have
SHORTEST_WAIT_SECONDS = "0.2"
PAST_THE_SHORTEST_WAIT_SECONDS = 0.6

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
    return await servers.start_change([one_line_file()])


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


async def test_a_thread_raised_hangs_on_the_side_it_names_with_the_weight_it_is_given(servers: ReviewServers) -> None:
    """A thread on lines the change removed must not land on the lines that replaced them."""
    review = await servers.start_change([diff_file(REVIEWED_FILE, [removed_line(1, "x = 0"), added_line(1, "x = 1")])])
    async with page_socket_held(review.port) as page:
        result = await _run(
            review, "point", "--file", REVIEWED_FILE, "--lines", "1", "--side", "old", "--severity", "blocker", "Why?"
        )
        raised = await asyncio.to_thread(next_push, page, PointPush)

    assert result.exit_code == 0, result.output
    assert (raised.anchor.side, raised.severity) == (LineSide.OLD, CommentSeverity.BLOCKER)


async def test_what_the_agent_says_names_the_files_it_is_about(review: RunningReview) -> None:
    async with page_socket_held(review.port) as page:
        result = await _run(review, "say", "--file", REVIEWED_FILE, "Renamed it")
        said = await asyncio.to_thread(next_push, page, ChatPush)

    assert result.exit_code == 0, result.output
    assert said.files == [REVIEWED_FILE]


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


async def test_the_work_reported_reaches_the_review_on_screen_and_goes_when_done(review: RunningReview) -> None:
    """What the agent says it is doing is drawn as it said it, and taken away when it says it is done."""
    async with page_socket_held(review.port) as page:
        await _run(review, "progress", "--message", "panel-1", "--file", REVIEWED_FILE, "rewriting the handler")
        work = await asyncio.to_thread(work_pushed, page)
        await _run(review, "progress", "--done")
        finished = await asyncio.to_thread(next_push, page, ProgressPush)

    assert (work.message_id, work.text, work.files) == ("panel-1", "rewriting the handler", [REVIEWED_FILE])
    assert finished.work is None


async def test_the_agent_reports_what_the_review_cannot_measure(review: RunningReview) -> None:
    """Which model, and how much context is left, come from the agent alone."""
    async with page_socket_held(review.port) as page:
        result = await _run(review, "status", "--model", "opus-5", "--context", "53% of 1M")
        pushed = await asyncio.to_thread(next_push, page, StatusPush)

    assert result.exit_code == 0, result.output
    assert (pushed.agent.model, pushed.agent.context) == ("opus-5", "53% of 1M")


async def test_a_thread_named_is_read_in_full(review: RunningReview) -> None:
    """The index is for choosing; naming a thread hands over all of it, with the lines it is about."""
    quoted = {**line_json(REVIEWED_FILE, 1), "quote": [REVIEWED_LINE]}
    written = thread_json(quoted, "Why this?\nAnd not that?")
    async with page_socket_held(review.port) as page:
        page.send(json.dumps({"threads": [written]}))
        with Client(base_url=review.url) as reader:
            await asyncio.to_thread(until_the_review_holds_threads, reader, 1)

        read = await _run(review, "catch-up", "--thread", FIRST_THREAD_ID)

    assert read.exit_code == 0, read.output
    assert "And not that?" in read.output
    assert f"lines: {REVIEWED_LINE}" in read.output


async def test_waiting_until_an_event_waits_through_the_timeouts(review: RunningReview) -> None:
    """The agent's loop is handed only what happened, never a timeout to look for and skip."""
    waiting = asyncio.create_task(_run(review, "wait", "--seconds", SHORTEST_WAIT_SECONDS, "--until-event"))
    # Long enough for the first wait to have timed out
    await asyncio.sleep(PAST_THE_SHORTEST_WAIT_SECONDS)
    async with AsyncClient(base_url=review.url) as page:
        await page.post(
            MESSAGE_ROUTE, json={"message_id": "panel-1", "body": "Still there?", "images": [], "threads": []}
        )

    assert json.loads((await waiting).output)["type"] == "message"


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
        await page.post(MESSAGE_ROUTE, json={"message_id": "panel-1", "body": HOSTILE, "images": [], "threads": []})

    result = await _run(review, *command)

    assert result.exit_code == 0, result.output
    assert _controls_in(result.output) == []
    assert "\\u001b]52" in result.output


async def test_what_is_handed_over_as_json_says_what_was_written(review: RunningReview) -> None:
    """Made safe for the terminal, it is still the JSON of what the reader wrote."""
    async with AsyncClient(base_url=review.url) as page:
        await page.post(MESSAGE_ROUTE, json={"message_id": "panel-1", "body": HOSTILE, "images": [], "threads": []})

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
    asked = {"question_id": FIRST_THREAD_ID, "thread": thread_json(line_json(REVIEWED_FILE, 1), "Why?")}
    async with AsyncClient(base_url=review.url) as reader, page_socket_held(review.port) as page:
        await reader.post(ASK_ROUTE, json=asked)
        result = await _run(review, "reply", "--thread", FIRST_THREAD_ID, FROM_STDIN, typed=FROM_A_HEREDOC)
        answered = await asyncio.to_thread(next_push, page, ReplyPush)

    assert result.exit_code == 0, result.output
    assert answered.body == MARKDOWN


STORY_ROUTE = "/api/story"
# What the repository under review has changed since its commit, and steps that tell each of the two changes
EDITED_FILE = "initial.txt"
ADDED_FILE = "src/added.py"
THE_CHANGE = {EDITED_FILE: "initial content\nand a line since\n", ADDED_FILE: "def added() -> None:\n    return None\n"}
THE_LINE_ADDED = step(EDITED_FILE, 2, 2)
THE_FILE_ADDED = step(ADDED_FILE, 1, 2)


@pytest.fixture
async def review_of_a_change(servers: ReviewServers, tmp_git_repo: Path) -> RunningReview:
    """A review of a repository's uncommitted changes, served on a port of its own."""
    write_files(tmp_git_repo, THE_CHANGE)
    return await servers.start(await repository_opening(tmp_git_repo))


async def _story_held(review: RunningReview) -> StoryResponse:
    """The story the review holds, as its page reads it."""
    async with AsyncClient(base_url=review.url) as page:
        return StoryResponse.model_validate_json((await page.get(STORY_ROUTE)).content)


async def test_a_story_written_to_a_file_is_told_and_answered_in_a_line(
    review_of_a_change: RunningReview, tmp_path: Path
) -> None:
    written = tmp_path / "story.json"
    written.write_text(json.dumps(as_the_agent_writes(story_of(THE_LINE_ADDED, THE_FILE_ADDED))))

    result = await _run(review_of_a_change, "story", "--file", str(written))

    assert result.exit_code == 0, result.output
    assert result.output == "accepted: 1 chapter, 2 steps; nothing left out\n"
    held = (await _story_held(review_of_a_change)).held
    assert held is not None
    assert [told.file for told in held.story.chapters[0].steps] == [EDITED_FILE, ADDED_FILE]


async def test_a_story_piped_in_is_told_and_what_it_leaves_out_is_said(review_of_a_change: RunningReview) -> None:
    """How many lines no step tells, and of which files: what the reader will be shown beside the story."""
    piped = json.dumps(as_the_agent_writes(story_of(THE_LINE_ADDED)))

    result = await _run(review_of_a_change, "story", "--file", FROM_STDIN, typed=piped)

    assert result.exit_code == 0, result.output
    assert result.output == f"accepted: 1 chapter, 1 step; 2 lines not in the story ({ADDED_FILE})\n"


async def test_a_story_the_review_refuses_fails_in_a_line_naming_everything_wrong_with_it(
    review_of_a_change: RunningReview,
) -> None:
    untitled = planted(story_of(THE_LINE_ADDED, step(ADDED_FILE, 7, 9)), ("title",), "")

    result = await _run(
        review_of_a_change, "story", "--file", FROM_STDIN, typed=json.dumps(as_the_agent_writes(untitled))
    )

    assert result.exit_code == FAILED
    assert "title: says nothing" in result.output
    assert "chapters.0.steps.1.lines: hold no line" in result.output
    assert (await _story_held(review_of_a_change)).held is None


async def test_a_first_story_the_reader_asks_for_is_printed_by_wait_as_its_kind_with_nothing_gone_stale(
    review_of_a_change: RunningReview,
) -> None:
    """The request says that a story is wanted: it is of the change the review holds, and no story told went stale."""
    async with AsyncClient(base_url=review_of_a_change.url) as page:
        await page.post(STORY_REQUEST_ROUTE)

    result = await _run(review_of_a_change, "wait", "--seconds", "5")

    assert result.output == '{"type":"story_request","stale":null}\n'


async def test_a_file_a_story_leaves_out_is_printed_to_be_read_never_obeyed(
    servers: ReviewServers, tmp_git_repo: Path
) -> None:
    """A file's name is the repository's to choose, and may hold what a terminal would act on: here, a clipboard write."""
    hostile_file = f"copied{ESCAPE}]52;c;ZWNobyBwd25lZA==\x07.py"
    write_files(tmp_git_repo, {**THE_CHANGE, hostile_file: "pass\n"})
    review = await servers.start(await repository_opening(tmp_git_repo))
    told = json.dumps(as_the_agent_writes(story_of(THE_LINE_ADDED, THE_FILE_ADDED)))

    result = await _run(review, "story", "--file", FROM_STDIN, typed=told)

    assert result.exit_code == 0, result.output
    assert "1 line not in the story" in result.output
    assert _controls_in(result.output) == []

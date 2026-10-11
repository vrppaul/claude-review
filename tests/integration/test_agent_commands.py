"""The agent's commands against a review served on a port: what is typed arrives as meant, or fails in a line.

Run in the test's own process, so a test reads what a command sent from the
review itself. The review answers on the test's loop, so each command runs
on a thread of its own, as it would in a process of its own.
"""

import asyncio
from http import HTTPStatus

import pytest
from click.testing import CliRunner, Result
from httpx import AsyncClient

from claude_review.cli.main import main
from claude_review.presentation.wire.agent import ProgressStep
from claude_review.presentation.wire.content import ReviewResponse
from tests.helpers import REVIEW_ROUTE, REVIEWED_FILE, ReviewServers, RunningReview, one_line_file, opening_of

# What a command that ran and failed exits with
FAILED = 1


@pytest.fixture
async def review(servers: ReviewServers) -> RunningReview:
    """A review of one file with one line in it, served on a port of its own."""
    return await servers.start(opening_of([one_line_file()]))


async def _run(review: RunningReview, command: str, *arguments: str) -> Result:
    """Run one of the agent's commands against the review, as the agent types it."""
    return await asyncio.to_thread(CliRunner().invoke, main, [command, "--port", str(review.port), *arguments])


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

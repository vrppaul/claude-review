"""E2E tests: full round-trip with real server and real browser."""

import asyncio
import json
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient, TransportError
from playwright.async_api import Locator, Page, expect

from claude_review.domain.models import ReviewMode
from claude_review.services.text_files import read_text_files
from claude_review.services.transcript import read_transcript
from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.helpers import (
    EVENTS_ROUTE,
    GLANCE_AT_EVENTS,
    SETTLE_SECONDS,
    ReviewServers,
    RunningReview,
    committed_repository,
    git,
    opening_of,
    repository_opening,
    review_has_ended,
    write_files,
)

# What the page posts when it sends the review, a round or the last of it
SUBMIT_RESPONSE = "**/api/submit"
# How long the agent's wait lasts, in the tests that start one: long enough for what the test sets going
AGENT_WAIT_SECONDS = 15

RAISED_BODY = "I kept the old name; renaming it broke two callers."
# The e2e repository: its file as committed, and the changes made since —
# that file edited, one added
MAIN_FILE = "main.py"
NEW_FILE = "new_file.ts"
COMMITTED_FILES = {MAIN_FILE: "def hello():\n    return 'hello'\n\ndef world():\n    return 'world'\n"}
CHANGES = {
    MAIN_FILE: "def hello():\n    return 'hi'\n\ndef world():\n    return 'world'\n",
    NEW_FILE: "export const x = 1;\nexport const y = 2;\nexport const z = 3;\n",
}
# What has the keyboard, by what it says it does
FOCUSED_LABEL = "document.activeElement?.getAttribute('aria-label')"
# A review long enough that its last file stands far further below the screen
# than a file is built ahead of being reached: files added whole, each of many lines
LONG_FILE_COUNT = 8
LONG_FILE_LINES = 60
LONG_FILES = {
    f"module_{number}.py": "".join(f"value_{line} = {line}\n" for line in range(LONG_FILE_LINES))
    for number in range(LONG_FILE_COUNT)
}
FIRST_LONG_FILE, *_, LAST_LONG_FILE = LONG_FILES
# A point on the page, in pixels, that no dialog in the middle of it covers, nor a pane under a control
OUTSIDE_THE_DIALOG = 5
# The conversation the transcript is written with, one entry a line: a question, and its answer
TRANSCRIPT_LINES = [
    json.dumps(
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": "can you refactor the auth module?\nuse JWT instead of sessions",
            },
        }
    ),
    json.dumps(
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "def authenticate(token):\n    return jwt.decode(token)"}],
            },
        }
    ),
]


def _section(page: Page, path_suffix: str) -> Locator:
    """One file's section in the stream.

    Every file is on screen at once, so a locator has to say which file it
    means — otherwise it matches the same control in each of them.
    """
    return page.locator(f'[data-testid="file-section"][data-path$="{path_suffix}"]')


def _first_gutter(page: Page, path_suffix: str) -> Locator:
    return _section(page, path_suffix).get_by_test_id("line-gutter").first


async def _send(page: Page) -> str:
    """Send what has been written: open the finishing pane, then send from it.

    One button in the header opens what used to be three: it shows what is
    about to go, takes a summary, and holds both ways out.
    """
    await page.get_by_test_id("quick-submit").click()
    return await _send_from_the_pane(page)


async def _send_from_the_pane(page: Page) -> str:
    """Send from the finishing pane already open, and return what the agent was handed."""
    async with page.expect_response(SUBMIT_RESPONSE) as submitted:
        await page.get_by_test_id("modal-submit").click()
    return (await (await submitted.value).json())["markdown"]


async def _agent(review: RunningReview, command: str, *arguments: str) -> str:
    """Run one of the agent's commands against the review, as the agent would, and return what it printed."""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "claude_review",
        command,
        "--port",
        str(review.port),
        *arguments,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    printed, said = await process.communicate()
    assert process.returncode == 0, said.decode()
    return printed.decode()


async def _next_event(review: RunningReview) -> dict:
    """Wait as the agent does for whatever the reader hands over next."""
    return json.loads(await _agent(review, "wait", "--seconds", str(AGENT_WAIT_SECONDS)))


async def _agent_hears_it_ended(review: RunningReview) -> bool:
    """Whether an agent asking now is told the review is over, or finds nobody listening.

    The page ends the review with a request of its own, which an agent's poll
    may beat, so it asks again until it hears. And the server stops a moment
    after the review ends, so a poll may find nobody there at all — which the
    skill tells the agent means the same.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + SETTLE_SECONDS
    while loop.time() < deadline:
        try:
            # A client of its own each time: one kept from before would reuse
            # a connection the stopping server has already let go
            async with AsyncClient(base_url=review.url) as agent:
                if await review_has_ended(agent):
                    return True
        except TransportError:
            return True
    return False


async def _click_line_and_comment(page: Page, line_locator: Locator, text: str) -> None:
    """Helper: click a line gutter and add a comment."""
    await line_locator.click()
    await page.get_by_test_id("comment-input").fill(text)
    await page.get_by_test_id("save-comment").click()
    await page.wait_for_selector(f"text={text}")


@pytest.fixture
def e2e_repo(tmp_path: Path) -> Path:
    """Create a git repo with several types of changes for e2e testing."""
    committed_repository(tmp_path, COMMITTED_FILES)
    write_files(tmp_path, CHANGES)
    git(tmp_path, "add", NEW_FILE)

    return tmp_path


@in_the_browsers_loop
async def diff_review(e2e_repo: Path, servers: ReviewServers) -> RunningReview:
    """A real server reviewing the e2e repo's uncommitted changes."""
    return await servers.start(await repository_opening(e2e_repo))


async def test_a_comment_on_a_line_reaches_the_agent(diff_review: RunningReview, page: Page) -> None:
    """Full round trip: see diff, add comment, submit, verify output."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    file_buttons = await page.get_by_test_id("file-item").all()
    assert len(file_buttons) >= 1

    line_cell = page.get_by_test_id("line-gutter").first
    await _click_line_and_comment(page, line_cell, "This needs fixing")

    sent = await _send(page)
    await page.get_by_test_id("submitted-banner").wait_for()

    assert "This needs fixing" in sent


@pytest.fixture
def text_files(tmp_path: Path) -> list[Path]:
    """Create text files for files-mode testing."""
    plan = tmp_path / "plan.md"
    plan.write_text("# My Plan\n\nStep 1: Do something\nStep 2: Do more\n")
    notes = tmp_path / "notes.md"
    notes.write_text("Some notes\nMore notes\n")
    return [plan, notes]


@in_the_browsers_loop
async def files_review(text_files: list[Path], servers: ReviewServers, tmp_path: Path) -> RunningReview:
    """A real server reviewing two text files."""
    return await servers.start(
        opening_of(await read_text_files(text_files, named_from=tmp_path), mode=ReviewMode.FILES)
    )


async def test_a_comment_on_a_file_reaches_the_agent(files_review: RunningReview, page: Page) -> None:
    """Full round-trip in files mode: click line, comment, submit, verify output."""
    await page.goto(files_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    line_cell = page.get_by_test_id("line-gutter").first
    await _click_line_and_comment(page, line_cell, "Plan needs more detail")

    sent = await _send(page)
    await page.get_by_test_id("submitted-banner").wait_for()

    assert "Plan needs more detail" in sent


@pytest.fixture
def transcript_file(tmp_path: Path) -> Path:
    """Create a JSONL conversation file for transcript-mode testing."""
    conversation = tmp_path / "conversation.jsonl"
    conversation.write_text("\n".join(TRANSCRIPT_LINES))
    return conversation


@in_the_browsers_loop
async def transcript_review(transcript_file: Path, servers: ReviewServers) -> RunningReview:
    """A real server reviewing a conversation."""
    return await servers.start(opening_of(await read_transcript(transcript_file), mode=ReviewMode.TRANSCRIPT))


async def test_a_comment_on_a_message_reaches_the_agent(transcript_review: RunningReview, page: Page) -> None:
    """Full round-trip in transcript mode: comment on message, submit, verify output."""
    await page.goto(transcript_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    line_cell = page.get_by_test_id("line-gutter").first
    await _click_line_and_comment(page, line_cell, "Wrong approach")

    sent = await _send(page)
    await page.get_by_test_id("submitted-banner").wait_for()

    assert "Transcript Review" in sent
    assert "Wrong approach" in sent


@in_the_browsers_loop
async def long_review(tmp_path: Path, servers: ReviewServers) -> RunningReview:
    """A real server reviewing more lines than are built before the reader comes near them."""
    repository = committed_repository(tmp_path, {"README.md": "# A long review\n"})
    write_files(repository, LONG_FILES)
    return await servers.start(await repository_opening(repository))


async def test_a_file_further_down_the_stream_is_built_as_it_is_approached_and_not_before(
    long_review: RunningReview, page: Page
) -> None:
    """A review of sixty files would build tens of thousands of rows before showing anything."""
    await page.goto(long_review.url)
    await _section(page, FIRST_LONG_FILE).get_by_test_id("raw-view").wait_for()
    last = _section(page, LAST_LONG_FILE)

    assert await last.get_by_test_id("file-placeholder").count() == 1
    assert await last.get_by_test_id("line-gutter").count() == 0

    await last.scroll_into_view_if_needed()

    await last.get_by_test_id("raw-view").wait_for()
    assert await last.get_by_test_id("line-gutter").count() == LONG_FILE_LINES


async def test_a_removed_line_beside_its_replacement_takes_a_comment_from_the_keyboard(
    diff_review: RunningReview, page: Page
) -> None:
    """In two columns line 2 of main.py faces the line that replaced it: Tab reaches it, Enter comments on it."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()
    await page.get_by_test_id("settings-toggle").click()
    await page.get_by_test_id("layout-split").click()
    await _section(page, MAIN_FILE).get_by_test_id("split-view").wait_for()
    await page.get_by_test_id("settings-toggle").click()

    await page.keyboard.press("j")
    await page.keyboard.press("Tab")
    reached = await page.evaluate("document.activeElement.getAttribute('aria-label')")
    await page.keyboard.press("Enter")

    assert reached == "Comment on removed line 2"
    await expect(_section(page, MAIN_FILE).get_by_text("Removed line 2")).to_be_visible()


async def test_question_mark_closes_the_keys_list_and_gives_the_keyboard_back(
    diff_review: RunningReview, page: Page
) -> None:
    """? opens the list and closes it again, as Escape does: the reader carries on from their line."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()
    await page.keyboard.press("j")
    await page.keyboard.press("j")
    reading = await page.evaluate(FOCUSED_LABEL)

    await page.keyboard.press("?")
    await page.get_by_test_id("help-menu").wait_for()
    await page.keyboard.press("?")
    await page.get_by_test_id("help-menu").wait_for(state="detached")

    assert await page.evaluate(FOCUSED_LABEL) == reading


async def test_a_press_outside_the_keys_list_closes_it_and_a_selection_let_go_there_does_not(
    diff_review: RunningReview, page: Page
) -> None:
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()
    await page.keyboard.press("?")
    help_menu = page.get_by_test_id("help-menu")
    await help_menu.wait_for()
    words = await page.get_by_text("Keyboard", exact=True).bounding_box()
    assert words is not None

    await page.mouse.move(words["x"] + 1, words["y"] + words["height"] / 2)
    await page.mouse.down()
    await page.mouse.move(OUTSIDE_THE_DIALOG, OUTSIDE_THE_DIALOG)
    await page.mouse.up()
    await expect(help_menu).to_be_visible()

    await page.mouse.click(OUTSIDE_THE_DIALOG, OUTSIDE_THE_DIALOG)
    await help_menu.wait_for(state="detached")


async def test_the_keyboard_leaving_a_pane_closes_it(diff_review: RunningReview, page: Page) -> None:
    """One pane at a time from the keyboard too: Tab out of the list of bases, and Enter on Finish."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()
    await page.get_by_test_id("base-picker").click()
    await page.get_by_test_id("base-option").first.wait_for()

    while await page.evaluate("document.activeElement?.dataset.testid") != "quick-submit":
        await page.keyboard.press("Tab")
    await page.keyboard.press("Enter")
    await page.get_by_test_id("finish-review").wait_for()

    assert await page.get_by_test_id("base-list").count() == 0


async def test_the_keyboard_comes_back_to_the_send_button_after_a_round(diff_review: RunningReview, page: Page) -> None:
    """The send button is disabled while the round goes, which takes the keyboard off it; it comes back."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()
    waiting = asyncio.create_task(_next_event(diff_review))
    await page.get_by_test_id("panel-input").wait_for()
    await _click_line_and_comment(page, _first_gutter(page, MAIN_FILE), "Round from the keyboard")

    await page.get_by_test_id("quick-submit").focus()
    await page.keyboard.press("Enter")
    await page.get_by_test_id("modal-submit").focus()
    await page.keyboard.press("Enter")
    await page.get_by_test_id("finish-review").wait_for(state="detached")

    assert (await waiting)["type"] == "round"
    assert await page.evaluate("document.activeElement?.dataset.testid") == "quick-submit"


async def test_comments_survive_a_reload(diff_review: RunningReview, page: Page) -> None:
    """A stray reload should not cost an hour of reading."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    await _click_line_and_comment(page, _first_gutter(page, MAIN_FILE), "Written before the reload")

    await page.reload()
    await page.get_by_test_id("restored-notice").wait_for()
    await page.wait_for_selector("text=Written before the reload")

    sent = await _send(page)
    await page.get_by_test_id("submitted-banner").wait_for()

    assert "Written before the reload" in sent


async def test_a_question_asked_in_a_thread_is_answered_in_it(diff_review: RunningReview, page: Page) -> None:
    """The whole round trip: asked in the browser, answered from outside it."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    # Asking is only offered while something is waiting to answer
    waiting = asyncio.create_task(_next_event(diff_review))
    await page.get_by_test_id("panel-input").wait_for()

    await _first_gutter(page, MAIN_FILE).click()
    await page.get_by_test_id("comment-input").fill("Was the old greeting used anywhere else?")
    await page.get_by_test_id("ask-now").click()
    await page.get_by_test_id("awaiting-answer").wait_for()

    asked = await waiting
    assert asked["question"]["body"] == "Was the old greeting used anywhere else?"
    assert asked["question"]["thread"]["anchor"]["quote"] == ["def hello():"]

    await _agent(
        diff_review,
        "reply",
        "--thread",
        asked["question"]["thread"]["thread_id"],
        "--question",
        asked["question"]["question_id"],
        "No, it was the only caller.",
    )

    answer = page.get_by_test_id("thread-answer")
    await answer.wait_for()
    assert "No, it was the only caller." in (await answer.text_content() or "")
    # And it is marked as something the reader has not looked at yet
    await page.get_by_test_id("comment-unread").wait_for()


async def test_a_round_is_sent_without_ending_the_review(diff_review: RunningReview, page: Page) -> None:
    """Rounds appear once something is waiting to answer them."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    # An agent waiting on the review is what makes a round worth offering
    waiting = asyncio.create_task(_next_event(diff_review))
    await page.get_by_test_id("panel-input").wait_for()

    await _click_line_and_comment(page, _first_gutter(page, MAIN_FILE), "Shorten this greeting")
    await _send(page)

    handed_over = await waiting
    assert handed_over["type"] == "round"
    assert "Shorten this greeting" in handed_over["round"]["markdown"]

    # The review is still open, with its threads on screen
    async with AsyncClient(base_url=diff_review.url) as agent:
        assert not await review_has_ended(agent)
        await page.wait_for_selector("text=Shorten this greeting")

        await page.get_by_test_id("quick-submit").click()
        await page.get_by_test_id("end-review").click()
        await page.get_by_test_id("submitted-banner").wait_for()

    assert await _agent_hears_it_ended(diff_review)


async def test_the_panel_carries_a_message_to_the_agent_and_back(diff_review: RunningReview, page: Page) -> None:
    """The whole round trip for what belongs to no line of the diff."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    # The panel shows itself once something is there to answer
    waiting = asyncio.create_task(_next_event(diff_review))
    await page.get_by_test_id("panel-input").wait_for()

    await page.get_by_test_id("panel-input").fill("Which tests cover this?")
    await page.get_by_test_id("send-message").click()
    await page.get_by_test_id("panel-working").wait_for()

    handed_over = await waiting
    assert handed_over["type"] == "message"
    assert handed_over["message"]["body"] == "Which tests cover this?"

    await _agent(
        diff_review, "say", "--message", handed_over["message"]["message_id"], "The e2e one, and two unit tests."
    )

    answer = page.get_by_test_id("panel-answer")
    await answer.wait_for()
    assert "The e2e one, and two unit tests." in (await answer.text_content() or "")


async def test_a_thread_the_author_raises_lands_on_the_line(diff_review: RunningReview, page: Page) -> None:
    """What belongs on the code goes on the code, and says whose it is."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    # Attaching is what shows the panel: a glance at the events attaches, and nothing has to be asked of it here
    async with AsyncClient(base_url=diff_review.url) as agent:
        await agent.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)
    await page.get_by_test_id("panel-input").wait_for()

    pointed = await _agent(diff_review, "point", "--file", MAIN_FILE, "--lines", "1", RAISED_BODY)
    assert json.loads(pointed)["thread_id"] == "raised-1"

    main = _section(page, MAIN_FILE)
    await main.get_by_text(RAISED_BODY).wait_for()
    # Drawn as the author's, and not counted as the reader's unsent work
    await main.get_by_test_id("comment-raised").wait_for()
    assert "0 unsent" in (await page.get_by_test_id("comment-count").text_content() or "")

    # And the panel says where it went
    await page.get_by_test_id("panel-thread-ref").wait_for()

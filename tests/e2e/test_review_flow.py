"""E2E tests: full round-trip with real server and real browser."""

import asyncio
import json
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient, TransportError
from playwright.async_api import Locator, Page, expect

from claude_review.domain.models import ReviewMode
from claude_review.hosting.workspace import ReaderFiles
from claude_review.services.text_files import read_text_files
from claude_review.services.transcript import read_transcript
from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.folds import CHEVRON, POINTING_DOWN, POINTING_UP, TURN
from tests.e2e.painted import on_a_probe, painted
from tests.helpers import (
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
# How long the agent's wait lasts, in the tests that start one: long enough
# for what the test sets going, and briefly when nothing will come
AGENT_WAIT_SECONDS = 15
BRIEF_AGENT_WAIT_SECONDS = 3

RAISED_BODY = "I kept the old name; renaming it broke two callers."
# The e2e repository: its files as committed, and the changes made since —
# one file edited, one added
MAIN_FILE = "main.py"
NEW_FILE = "new_file.ts"
UTILS_FILE = "utils.py"
COMMITTED_FILES = {
    MAIN_FILE: "def hello():\n    return 'hello'\n\ndef world():\n    return 'world'\n",
    UTILS_FILE: "# utils\n",
}
CHANGES = {
    MAIN_FILE: "def hello():\n    return 'hi'\n\ndef world():\n    return 'world'\n",
    NEW_FILE: "export const x = 1;\nexport const y = 2;\nexport const z = 3;\n",
}
# The files the e2e repository's uncommitted changes touch
CHANGED_FILES = tuple(CHANGES)
# What moves under a review after its diff was taken: two files the reader has not been shown again
MOVED_AFTER_THE_RETAKE = {MAIN_FILE: "def hello():\n    return 'hey'\n", UTILS_FILE: "# utils, rewritten\n"}
# What the sidebar's filter is typed with to find the added file alone
NEW_FILE_TYPED = Path(NEW_FILE).stem
# What has the keyboard, by what it says it does
FOCUSED_LABEL = "document.activeElement?.getAttribute('aria-label')"
# Where an element's right edge is on screen; where what an element holds ends, short of its padding; and where
# the chip a checkbox stands in ends
RIGHT_OF = "(element) => element.getBoundingClientRect().right"
INNER_RIGHT_OF = (
    "(element) => element.getBoundingClientRect().right - parseFloat(getComputedStyle(element).paddingRight)"
)
CHIP_RIGHT_OF = "(box) => box.closest('label').getBoundingClientRect().right"
# A review long enough that its last file stands far further below the screen
# than a file is built ahead of being reached: files added whole, each of many lines
LONG_FILE_COUNT = 8
LONG_FILE_LINES = 60
LONG_FILES = {
    f"module_{number}.py": "".join(f"value_{line} = {line}\n" for line in range(LONG_FILE_LINES))
    for number in range(LONG_FILE_COUNT)
}
FIRST_LONG_FILE, *_, LAST_LONG_FILE = LONG_FILES
# What a round heads each thread with
THREAD_HEADING = "### "
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
TRANSCRIPT_TURNS = len(TRANSCRIPT_LINES)


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


async def _next_event(review: RunningReview, seconds: int = AGENT_WAIT_SECONDS) -> dict:
    """Wait as the agent does for whatever the reader hands over next."""
    return json.loads(await _agent(review, "wait", "--seconds", str(seconds)))


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


def _heading_above(sent: str, said: str) -> str:
    """The heading of the thread in a round that says something: the last one above it."""
    lines = sent.splitlines()
    said_at = next(number for number, line in enumerate(lines) if said in line)
    return next(line for line in reversed(lines[:said_at]) if line.startswith(THREAD_HEADING))


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


async def test_a_comment_dragged_over_lines_names_the_range(diff_review: RunningReview, page: Page) -> None:
    """Drag creates a range comment (e.g. file:1-3)."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    gutters = _section(page, MAIN_FILE).get_by_test_id("line-gutter")
    await gutters.first.dispatch_event("mousedown")
    await gutters.nth(4).dispatch_event("mouseenter")
    await _section(page, MAIN_FILE).get_by_test_id("raw-view").dispatch_event("mouseup")

    await page.get_by_test_id("comment-input").fill("Refactor this range")
    await page.get_by_test_id("save-comment").click()
    await page.wait_for_selector("text=Refactor this range")

    sent = await _send(page)
    await page.get_by_test_id("submitted-banner").wait_for()

    assert "Refactor this range" in sent
    # From the first line of the hunk to the fourth of the new file
    assert f"### `{MAIN_FILE}`:1-4" in sent


async def test_comments_on_several_files_are_each_filed_under_their_own(diff_review: RunningReview, page: Page) -> None:
    """Comments across multiple files all appear in output."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    assert len(await page.get_by_test_id("file-item").all()) == len(CHANGED_FILES)

    # Both files are already on screen, so neither comment needs navigation
    await _click_line_and_comment(page, _first_gutter(page, MAIN_FILE), "Comment on main")
    await _click_line_and_comment(page, _first_gutter(page, NEW_FILE), "Comment on new file")

    sent = await _send(page)
    await page.get_by_test_id("submitted-banner").wait_for()

    assert MAIN_FILE in sent
    assert NEW_FILE in sent
    # Each comment is filed under the file it was left on, not both under one
    assert sent.index("Comment on main") < sent.index(NEW_FILE)


async def test_a_summary_and_a_comment_are_sent_together(diff_review: RunningReview, page: Page) -> None:
    """Add inline comment, then open modal to add summary, submit from modal."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    line_cell = page.get_by_test_id("line-gutter").first
    await _click_line_and_comment(page, line_cell, "Fix this line")

    await page.get_by_test_id("quick-submit").click()
    await page.get_by_test_id("finish-comment").wait_for()

    modal_textarea = page.get_by_test_id("review-body")
    await modal_textarea.fill("Generally good.")

    sent = await _send_from_the_pane(page)
    await page.get_by_test_id("submitted-banner").wait_for()

    assert "Generally good." in sent
    assert "Fix this line" in sent


async def test_nothing_written_means_nothing_to_send(diff_review: RunningReview, page: Page) -> None:
    """Neither the button nor the shortcut sends an empty review."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    requested: list[str] = []
    page.on("request", lambda request: requested.append(request.url))

    await page.get_by_test_id("quick-submit").click()
    assert await page.get_by_test_id("modal-submit").is_disabled()

    await page.keyboard.press("Control+Shift+Enter")
    # Requests are reported in the order the page makes them: once this one
    # is seen, a send the shortcut made would have been seen before it
    async with page.expect_request("**/api/versions"):
        await page.evaluate("fetch('/api/versions')")

    assert not any("/api/submit" in address for address in requested)


async def test_a_summary_on_its_own_is_a_review(diff_review: RunningReview, page: Page) -> None:
    """The header and the dialog agree on what counts as something to send."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.get_by_test_id("quick-submit").click()
    await page.get_by_test_id("review-body").fill("The shape is right; the naming needs work.")

    assert not await page.get_by_test_id("modal-submit").is_disabled()

    sent = await _send_from_the_pane(page)
    await page.get_by_test_id("submitted-banner").wait_for()

    assert "The shape is right" in sent


async def test_closing_the_pane_keeps_the_summary_being_written(diff_review: RunningReview, page: Page) -> None:
    """Esc closes the pane and gives the keyboard back; reopening keeps the typed text."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    # Open it and type
    await page.get_by_test_id("quick-submit").click()
    modal_textarea = page.get_by_test_id("review-body")
    await modal_textarea.fill("Draft feedback")

    # Close with Esc: the keyboard goes back to the button that opened it
    await page.keyboard.press("Escape")
    await page.get_by_test_id("finish-review").wait_for(state="detached")
    focused = await page.evaluate("document.activeElement?.dataset.testid")
    assert focused == "quick-submit"

    # Reopen — text should still be there
    await page.get_by_test_id("quick-submit").click()
    modal_textarea = page.get_by_test_id("review-body")
    assert await modal_textarea.input_value() == "Draft feedback"


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


async def test_files_mode_sidebar_shows_files_without_diff_decorations(
    files_review: RunningReview, text_files: list[Path], page: Page
) -> None:
    """Sidebar shows plain file list — no status badges, no +/- stats."""
    await page.goto(files_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    heading = await page.get_by_test_id("sidebar-heading").text_content()
    assert heading == f"{len(text_files)} files"

    file_buttons = await page.get_by_test_id("file-item").all()
    assert len(file_buttons) == len(text_files)


async def test_a_comment_on_a_file_reaches_the_agent(files_review: RunningReview, page: Page) -> None:
    """Full round-trip in files mode: click line, comment, submit, verify output."""
    await page.goto(files_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    line_cell = page.get_by_test_id("line-gutter").first
    await _click_line_and_comment(page, line_cell, "Plan needs more detail")

    sent = await _send(page)
    await page.get_by_test_id("submitted-banner").wait_for()

    assert "Plan needs more detail" in sent


async def test_comments_on_several_files_all_reach_the_agent(
    files_review: RunningReview, text_files: list[Path], page: Page
) -> None:
    """Comments on different files all appear in the submission output."""
    await page.goto(files_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    await _click_line_and_comment(page, _first_gutter(page, "plan.md"), "Comment on plan")

    file_buttons = await page.get_by_test_id("file-item").all()
    assert len(file_buttons) == len(text_files)
    await file_buttons[1].click()
    await _first_gutter(page, "notes.md").wait_for()

    await _click_line_and_comment(page, _first_gutter(page, "notes.md"), "Comment on notes")

    sent = await _send(page)
    await page.get_by_test_id("submitted-banner").wait_for()

    assert "plan.md" in _heading_above(sent, "Comment on plan")
    assert "notes.md" in _heading_above(sent, "Comment on notes")


async def test_a_markdown_file_can_be_read_raw_rendered_or_both(files_review: RunningReview, page: Page) -> None:
    """Markdown files show the content view toggle in the header."""
    await page.goto(files_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    plan = _section(page, "plan.md")
    toggle = plan.get_by_test_id("content-view-toggle")
    await toggle.wait_for()
    assert await toggle.is_visible()

    assert await plan.get_by_test_id("view-mode-raw").is_visible()
    assert await plan.get_by_test_id("view-mode-preview").is_visible()
    assert await plan.get_by_test_id("view-mode-side-by-side").is_visible()


async def test_markdown_preview_renders_content(files_review: RunningReview, page: Page) -> None:
    """Switching to preview mode renders markdown as HTML."""
    await page.goto(files_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    plan = _section(page, "plan.md")
    await plan.get_by_test_id("view-mode-preview").click()
    await plan.get_by_test_id("preview-view").wait_for()

    # plan.md contains "# My Plan" which should render as an h1
    heading = plan.get_by_test_id("markdown-content").locator("h1")
    await heading.wait_for()
    assert await heading.text_content() == "My Plan"


async def test_side_by_side_shows_both_panes(files_review: RunningReview, page: Page) -> None:
    """Side-by-side mode shows raw view and rendered markdown."""
    await page.goto(files_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    plan = _section(page, "plan.md")
    await plan.get_by_test_id("view-mode-side-by-side").click()
    await plan.get_by_test_id("side-by-side-view").wait_for()

    # Left pane: raw view with line gutters
    assert await plan.get_by_test_id("raw-view").is_visible()
    assert len(await plan.get_by_test_id("line-gutter").all()) > 0

    # Right pane: rendered markdown
    assert await plan.get_by_test_id("markdown-content").first.is_visible()


async def test_commenting_works_in_side_by_side(files_review: RunningReview, page: Page) -> None:
    """Adding a comment in the left pane of side-by-side mode works."""
    await page.goto(files_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    plan = _section(page, "plan.md")
    await plan.get_by_test_id("view-mode-side-by-side").click()
    await plan.get_by_test_id("side-by-side-view").wait_for()

    await _click_line_and_comment(page, _first_gutter(page, "plan.md"), "Side-by-side comment")

    sent = await _send(page)
    await page.get_by_test_id("submitted-banner").wait_for()

    assert "Side-by-side comment" in sent


async def test_one_view_choice_holds_for_every_markdown_file(files_review: RunningReview, page: Page) -> None:
    """Switching one markdown file to preview switches them all: it is one setting for the review."""
    await page.goto(files_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    # The choice is one setting for the whole review, so switching it on one
    # markdown file applies to every other one in the stream
    await _section(page, "plan.md").get_by_test_id("view-mode-preview").click()

    await _section(page, "plan.md").get_by_test_id("preview-view").wait_for()
    assert await _section(page, "notes.md").get_by_test_id("preview-view").is_visible()


async def test_preview_shows_comment_badge(files_review: RunningReview, page: Page) -> None:
    """Adding comments in raw mode shows a badge when switching to preview."""
    await page.goto(files_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    # Add a comment in raw mode
    await _click_line_and_comment(page, _first_gutter(page, "plan.md"), "Needs work")

    # Switch to preview — badge should show
    plan = _section(page, "plan.md")
    await plan.get_by_test_id("view-mode-preview").click()
    await plan.get_by_test_id("preview-view").wait_for()

    badge = plan.get_by_test_id("preview-comment-badge")
    await badge.wait_for()
    badge_text = await badge.text_content()
    assert badge_text is not None
    assert "1 comment" in badge_text
    assert "Raw" in badge_text


async def test_code_files_offer_no_markdown_preview(diff_review: RunningReview, page: Page) -> None:
    """Non-markdown files (e.g. .py, .ts) do not show the view toggle."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    toggle = page.get_by_test_id("content-view-toggle")
    assert await toggle.count() == 0


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


async def test_transcript_mode_sidebar_shows_messages(transcript_review: RunningReview, page: Page) -> None:
    """Sidebar shows message list with 'Messages' header."""
    await page.goto(transcript_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    heading = await page.get_by_test_id("sidebar-heading").text_content()
    assert heading == f"{TRANSCRIPT_TURNS} messages"

    file_buttons = await page.get_by_test_id("file-item").all()
    assert len(file_buttons) == TRANSCRIPT_TURNS


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


async def test_every_file_is_on_screen_at_once(diff_review: RunningReview, page: Page) -> None:
    """The diff reads as one stream: no file has to be selected to be seen."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    sections = page.get_by_test_id("file-section")
    await sections.first.wait_for()

    file_count = len(await page.get_by_test_id("file-item").all())
    assert await sections.count() == file_count


async def test_folding_a_file_hides_its_lines(diff_review: RunningReview, page: Page) -> None:
    """A file can be folded away without leaving the stream."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    main = _section(page, MAIN_FILE)
    await main.get_by_test_id("raw-view").wait_for()

    await main.get_by_test_id("collapse-file").click()
    await main.get_by_test_id("raw-view").wait_for(state="detached")

    # The other files are untouched
    assert await _section(page, NEW_FILE).get_by_test_id("raw-view").is_visible()


async def test_a_files_fold_is_the_last_thing_in_its_header_pointing_up_while_open_and_down_once_folded(
    diff_review: RunningReview, page: Page
) -> None:
    await page.goto(diff_review.url)
    main = _section(page, MAIN_FILE)
    await main.get_by_test_id("raw-view").wait_for()
    fold = main.get_by_test_id("collapse-file")
    header_right = await main.get_by_test_id("file-header").evaluate(INNER_RIGHT_OF)
    viewed_right = await main.get_by_test_id("viewed-toggle").evaluate(CHIP_RIGHT_OF)

    assert viewed_right < await fold.evaluate(RIGHT_OF) <= header_right
    await expect(fold.locator(CHEVRON)).to_have_css(TURN, POINTING_UP)
    await fold.click()
    await expect(fold.locator(CHEVRON)).to_have_css(TURN, POINTING_DOWN)


async def test_marking_a_file_viewed_folds_it(diff_review: RunningReview, page: Page) -> None:
    """Marking a file done folds it, the way a long review needs."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    main = _section(page, MAIN_FILE)
    await main.get_by_test_id("raw-view").wait_for()

    await main.get_by_test_id("viewed-toggle").check()
    await main.get_by_test_id("raw-view").wait_for(state="detached")


async def test_a_file_marked_viewed_steps_back_into_faint_words(diff_review: RunningReview, page: Page) -> None:
    """What the reader has finished with says its name in faint words, which still read: a file not viewed does not."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()
    main = _section(page, MAIN_FILE)
    faint = await on_a_probe(page, "color", "var(--cr-faint)")

    await main.get_by_test_id("viewed-toggle").check()

    assert (await painted(main.get_by_test_id("file-heading"))).words == faint
    assert (await painted(_section(page, NEW_FILE).get_by_test_id("file-heading"))).words != faint


async def test_filtering_the_sidebar_narrows_the_list(diff_review: RunningReview, page: Page) -> None:
    """A long review is navigated by narrowing the list, not by scrolling it."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.get_by_test_id("file-filter").fill(NEW_FILE_TYPED)

    items = await page.get_by_test_id("file-item").all()
    assert len(items) == 1
    text = await items[0].text_content()
    assert text is not None
    assert NEW_FILE in text


async def test_sidebar_counts_files_marked_viewed(diff_review: RunningReview, page: Page) -> None:
    """Progress through a review is visible without counting rows by eye."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    await _section(page, MAIN_FILE).get_by_test_id("viewed-toggle").check()

    heading = page.get_by_test_id("sidebar-heading")
    await heading.filter(has_text="1 viewed").wait_for()


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


async def test_scrolling_to_a_file_from_the_sidebar_shows_its_lines(long_review: RunningReview, page: Page) -> None:
    """The sidebar moves the reader, and the file it lands on is ready to read."""
    await page.goto(long_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.get_by_test_id("file-item").filter(has_text=LAST_LONG_FILE).click()

    last = _section(page, LAST_LONG_FILE)
    await expect(last).to_be_in_viewport()
    await last.get_by_test_id("raw-view").wait_for()


async def test_split_layout_faces_the_two_versions(diff_review: RunningReview, page: Page) -> None:
    """A replacement can be read across rather than down."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.get_by_test_id("settings-toggle").click()
    await page.get_by_test_id("layout-split").click()

    main = _section(page, MAIN_FILE)
    await main.get_by_test_id("split-view").wait_for()
    assert await main.get_by_test_id("raw-view").count() == 0


async def test_comment_left_in_split_layout_reaches_claude(diff_review: RunningReview, page: Page) -> None:
    """Commenting works the same in either layout."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.get_by_test_id("settings-toggle").click()
    await page.get_by_test_id("layout-split").click()
    main = _section(page, MAIN_FILE)
    await main.get_by_test_id("split-view").wait_for()

    await _click_line_and_comment(page, main.get_by_test_id("line-gutter").first, "Split comment")

    sent = await _send(page)
    await page.get_by_test_id("submitted-banner").wait_for()

    assert "Split comment" in sent


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


async def test_a_comment_can_be_left_without_a_mouse(diff_review: RunningReview, page: Page) -> None:
    """The tool's central action has a keyboard path."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.keyboard.press("j")
    await page.keyboard.press("Enter")

    await page.get_by_test_id("comment-input").wait_for()
    await page.keyboard.type("Typed, not clicked")
    await page.keyboard.press("Control+Enter")
    await page.wait_for_selector("text=Typed, not clicked")

    await page.keyboard.press("Control+Shift+Enter")
    sent = await _send_from_the_pane(page)
    await page.get_by_test_id("submitted-banner").wait_for()

    assert "Typed, not clicked" in sent


async def test_j_and_k_move_between_lines(diff_review: RunningReview, page: Page) -> None:
    """Moving is moving focus, so the browser keeps the cursor on screen."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.keyboard.press("j")
    first = await page.evaluate("document.activeElement.getAttribute('aria-label')")
    await page.keyboard.press("j")
    second = await page.evaluate("document.activeElement.getAttribute('aria-label')")
    await page.keyboard.press("k")
    back = await page.evaluate("document.activeElement.getAttribute('aria-label')")

    assert first != second
    assert back == first


async def test_question_mark_shows_the_keys(diff_review: RunningReview, page: Page) -> None:
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.keyboard.press("?")
    await page.get_by_test_id("shortcuts-list").wait_for()

    await page.keyboard.press("Escape")
    await page.get_by_test_id("shortcuts-list").wait_for(state="detached")


async def test_the_keys_list_opens_as_a_pane_under_help_takes_the_keyboard_and_gives_it_back_on_escape(
    diff_review: RunningReview, page: Page
) -> None:
    """A pane, as Settings is: under its control, the keyboard in it, headed, and closed by Escape or its own button."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()
    await page.get_by_test_id("open-help").focus()

    await page.keyboard.press("Enter")
    help_menu = page.get_by_test_id("help-menu")
    await help_menu.wait_for()
    assert await help_menu.evaluate("pane => pane.contains(document.activeElement)")
    await expect(help_menu.get_by_role("heading", name="Help", exact=True)).to_be_visible()
    help_top = await help_menu.evaluate("(pane) => pane.getBoundingClientRect().top")
    assert help_top >= await page.get_by_test_id("open-help").evaluate("(help) => help.getBoundingClientRect().bottom")

    await page.keyboard.press("Escape")
    await help_menu.wait_for(state="detached")
    focused = await page.evaluate("document.activeElement?.dataset.testid")
    assert focused == "open-help"

    await page.get_by_test_id("open-help").click()
    await help_menu.get_by_test_id("close-help").click()
    await help_menu.wait_for(state="detached")


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


async def test_the_finishing_pane_opened_from_a_comment_gives_the_keyboard_back_to_it(
    diff_review: RunningReview, page: Page
) -> None:
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()
    await page.keyboard.press("j")
    await page.keyboard.press("Enter")
    await page.get_by_test_id("comment-input").wait_for()
    await page.keyboard.type("Half a thought")

    await page.keyboard.press("Control+Shift+Enter")
    await page.get_by_test_id("finish-review").wait_for()
    await page.keyboard.press("Escape")
    await page.get_by_test_id("finish-review").wait_for(state="detached")

    assert await page.evaluate("document.activeElement?.dataset.testid") == "comment-input"


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


async def test_v_marks_the_file_you_are_in_as_viewed(diff_review: RunningReview, page: Page) -> None:
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.keyboard.press("j")
    await page.keyboard.press("v")

    await page.get_by_test_id("sidebar-heading").filter(has_text="1 viewed").wait_for()


async def test_typing_a_comment_does_not_trigger_shortcuts(diff_review: RunningReview, page: Page) -> None:
    """The letters that move around must still be letters inside a comment."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.keyboard.press("j")
    await page.keyboard.press("Enter")
    await page.get_by_test_id("comment-input").wait_for()
    await page.keyboard.type("just keep vjunk pn")

    assert await page.get_by_test_id("comment-input").input_value() == "just keep vjunk pn"


async def test_a_suggestion_reaches_claude_as_a_replacement(diff_review: RunningReview, page: Page) -> None:
    """Saying what the code should be beats describing it."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    await _first_gutter(page, MAIN_FILE).click()
    await page.get_by_test_id("comment-input").fill("Return the greeting we agreed on")
    await page.get_by_test_id("suggest-change").click()

    await page.get_by_test_id("save-comment").click()
    sent = await _send(page)
    await page.get_by_test_id("submitted-banner").wait_for()

    assert "```suggestion" in sent
    assert "Return the greeting we agreed on" in sent


async def test_ignoring_whitespace_retakes_the_diff(diff_review: RunningReview, page: Page) -> None:
    """The toggle asks git again rather than filtering what is already loaded."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    before = await page.get_by_test_id("file-section").count()
    await page.get_by_test_id("settings-toggle").click()
    async with page.expect_response(lambda response: "/api/diff?ignore_whitespace=true" in response.url) as asked:
        await page.get_by_test_id("ignore-whitespace").check()

    assert (await asked.value).ok
    # Nothing in the fixture is whitespace-only, so the review is unchanged —
    # what matters is that it came back rather than emptying out
    await expect(page.get_by_test_id("file-section")).to_have_count(before)


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


async def test_a_second_round_carries_only_what_is_new(diff_review: RunningReview, page: Page) -> None:
    """A round is what has been written since the last one, not the review again."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    first = asyncio.create_task(_next_event(diff_review))
    await page.get_by_test_id("panel-input").wait_for()

    await _click_line_and_comment(page, _first_gutter(page, MAIN_FILE), "Shorten this greeting")
    await _send(page)
    await first

    second = asyncio.create_task(_next_event(diff_review))
    await _click_line_and_comment(page, _first_gutter(page, NEW_FILE), "And name this properly")
    await _send(page)

    round_two = await second
    assert "round 2" in round_two["round"]["markdown"]
    assert "And name this properly" in round_two["round"]["markdown"]
    assert "Shorten this greeting" not in round_two["round"]["markdown"]


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


async def test_a_message_carries_the_thread_it_points_at(diff_review: RunningReview, page: Page) -> None:
    """Pointing at a thread saves retyping which line it was, and losing it."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    waiting = asyncio.create_task(_next_event(diff_review))
    await page.get_by_test_id("panel-input").wait_for()

    await _click_line_and_comment(page, _first_gutter(page, MAIN_FILE), "Is this greeting used?")

    await page.get_by_test_id("panel-input").fill("Look again at @")
    await page.get_by_test_id("thread-option").first.click()
    await page.get_by_test_id("send-message").click()

    handed_over = await waiting
    [thread] = handed_over["message"]["threads"]
    assert thread["body"] == "Is this greeting used?"
    assert thread["anchor"]["quote"] == ["def hello():"]


async def test_a_thread_pointed_at_in_a_message_being_written_is_a_chip_as_tall_as_once_sent_its_cross_in_its_colour(
    diff_review: RunningReview, page: Page
) -> None:
    """The way to take a thread out of a message stands inside its chip, which it neither grows nor recolours."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()
    waiting = asyncio.create_task(_next_event(diff_review))
    await page.get_by_test_id("panel-input").wait_for()
    await _click_line_and_comment(page, _first_gutter(page, MAIN_FILE), "Is this greeting used?")
    await page.get_by_test_id("panel-input").fill("Look again at @")
    await page.get_by_test_id("thread-option").first.click()
    being_written = await painted(page.get_by_test_id("pointed-thread"))
    cross = await painted(page.get_by_test_id("drop-thread"))

    await page.get_by_test_id("send-message").click()
    await waiting

    sent = await painted(page.get_by_test_id("panel-thread-ref"))
    assert (being_written.height, cross.words) == (sent.height, being_written.words)


async def test_the_review_says_when_the_tree_moves_under_it(e2e_repo: Path, servers: ReviewServers, page: Page) -> None:
    """Said, never acted on: the reader decides when to take the diff again."""
    review = await servers.start(await repository_opening(e2e_repo))
    async with AsyncClient(base_url=review.url) as agent:
        # Taken again, as the agent does after a round: the tree it is compared against is this one
        await agent.post("/api/retake", json={})
    write_files(e2e_repo, MOVED_AFTER_THE_RETAKE)

    await page.goto(review.url)

    notice = page.get_by_test_id("tree-moved")
    await notice.wait_for()
    said = " ".join((await notice.text_content() or "").split())
    assert f"{len(MOVED_AFTER_THE_RETAKE)} files have changed" in said

    await page.get_by_test_id("dismiss-moved").click()
    assert await notice.count() == 0


async def test_a_thread_the_author_raises_lands_on_the_line(diff_review: RunningReview, page: Page) -> None:
    """What belongs on the code goes on the code, and says whose it is."""
    await page.goto(diff_review.url)
    await page.get_by_test_id("sidebar").wait_for()

    # Attaching is what shows the panel; nothing has to be asked of it here
    waiting = asyncio.create_task(_next_event(diff_review, BRIEF_AGENT_WAIT_SECONDS))
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

    assert (await waiting)["type"] == "timeout"


async def test_a_first_review_is_welcomed_and_shown_around(
    diff_review: RunningReview, reader_files: ReaderFiles, page: Page
) -> None:
    """Somebody who has never opened a review is offered the tour, once."""
    reader_files.guide.unlink()
    await page.goto(diff_review.url)
    await page.get_by_test_id("guide-welcome").wait_for()

    await page.get_by_test_id("guide-start").click()
    await page.get_by_test_id("guide-tour").wait_for()
    await page.get_by_test_id("tour-spotlight").wait_for()
    await page.get_by_test_id("guide-skip").click()

    # Seen once, remembered for every review on this machine
    await page.reload()
    await page.get_by_test_id("sidebar").wait_for()
    assert await page.get_by_test_id("guide-welcome").count() == 0

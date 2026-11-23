"""E2E: a retake keeps the reader in the file they were reading.

The agent's work changes what is drawn above the reader as well as where
they are. The browser keeps the reader in place while the rows they look
at stay on the page; when the work rewrites the very file being read, its
rows are drawn afresh, and a page that keeps its scroll offset across the
new diff puts the reader in another file. What is in view is the browser's
alone: jsdom lays nothing out.
"""

from pathlib import Path

import pytest
from httpx2 import AsyncClient
from playwright.async_api import Locator, Page, ViewportSize, expect

from claude_review.domain.models import CommentSeverity
from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.page_reads import BROUGHT_TO_THE_TOP, FRAMES_DRAWN
from tests.helpers import (
    ReviewServers,
    RunningReview,
    committed_repository,
    pointed_json,
    repository_opening,
    write_files,
)
from tests.stories import as_the_agent_writes, step, story_of

# Three files, each changed far down: one above the file being read, and one
# below it changed on enough lines that the line read can be scrolled to the top
ABOVE_FILE = "above.py"
READ_FILE = "read.py"
BELOW_FILE = "zz_below.py"
# A file the change does not touch, read alone
LEFT_FILE = "left.py"
FILE_LENGTH = 200
CHANGED_LINE = 100
CHANGED_BELOW = range(50, 110)
# Where the agent's work adds lines in the file above and in the file being
# read, and how many: enough rows to move everything below by more than a screen
GROWN_AT = 10
GROWN_BY = 80
# A screen short enough that the files do not all fit on it
SCREEN: ViewportSize = {"width": 1280, "height": 600}
# The frames the page takes to see the line the reader reads from once it is brought to the top
FRAMES_TO_SEE_THE_LINE_READ = 2


def _lines(path: str, changed: dict[int, str] | None = None) -> str:
    """A file of numbered lines, some of them changed."""
    return "".join(f"{(changed or {}).get(number, f'{path} line {number}')}\n" for number in range(1, FILE_LENGTH + 1))


def _grown(path: str) -> str:
    """The file as the agent's work leaves it: lines added near its top, its change still there."""
    added = "\n".join(f"{path} grown {count}" for count in range(GROWN_BY))
    return _lines(path, {GROWN_AT: f"grown here\n{added}", CHANGED_LINE: "changed"})


@pytest.fixture
def three_files(tmp_path: Path) -> Path:
    """A repository where every file changed far down."""
    paths = (ABOVE_FILE, READ_FILE, BELOW_FILE)
    repo = committed_repository(tmp_path / "repo", {path: _lines(path) for path in paths})
    write_files(repo, {path: _lines(path, {CHANGED_LINE: "changed"}) for path in (ABOVE_FILE, READ_FILE)})
    write_files(repo, {BELOW_FILE: _lines(BELOW_FILE, dict.fromkeys(CHANGED_BELOW, "changed"))})
    return repo


@in_the_browsers_loop
async def review(three_files: Path, servers: ReviewServers) -> RunningReview:
    return await servers.start(await repository_opening(three_files))


def _section(page: Page, path: str) -> Locator:
    return page.locator(f'[data-testid="file-section"][data-path="{path}"]')


async def test_a_retake_that_rewrites_the_file_being_read_keeps_the_reader_in_it(
    review: RunningReview, three_files: Path, page: Page
) -> None:
    await page.set_viewport_size(SCREEN)
    await page.goto(review.url)
    # The reader reads the changed line of the file, brought to the top of the area
    read = _section(page, READ_FILE).get_by_role("button", name=f"Comment on line {CHANGED_LINE}", exact=True)
    await read.scroll_into_view_if_needed()
    await read.evaluate(BROUGHT_TO_THE_TOP)

    # The agent's work grows the file above and the file being read, above the line read, and retakes the diff
    write_files(three_files, {ABOVE_FILE: _grown(ABOVE_FILE), READ_FILE: _grown(READ_FILE)})
    async with AsyncClient(base_url=review.url) as agent:
        await agent.post("/api/retake", json={})
    await page.get_by_text(f"{READ_FILE} grown {GROWN_BY - 1}", exact=True).wait_for(state="attached")

    await expect(_section(page, READ_FILE)).to_be_in_viewport()


@pytest.fixture
def a_file_left_alone(tmp_path: Path) -> Path:
    """A repository where one file changed on enough lines to scroll, and another the change did not touch."""
    paths = (ABOVE_FILE, LEFT_FILE)
    repo = committed_repository(tmp_path / "repo", {path: _lines(path) for path in paths})
    write_files(repo, {ABOVE_FILE: _lines(ABOVE_FILE, dict.fromkeys(CHANGED_BELOW, "changed"))})
    return repo


@in_the_browsers_loop
async def review_with_a_thread_on_the_file_left(a_file_left_alone: Path, servers: ReviewServers) -> RunningReview:
    """The review, with a thread the agent raised on a line far down the file the change did not touch."""
    review = await servers.start(await repository_opening(a_file_left_alone))
    raised = {
        "lines": pointed_json(LEFT_FILE, CHANGED_LINE),
        "body": "the agent forgot this",
        "severity": CommentSeverity.NOTE,
    }
    async with AsyncClient(base_url=review.url) as agent:
        (await agent.post("/api/point", json=raised)).raise_for_status()
    return review


async def test_a_retake_that_leaves_a_file_read_alone_untouched_keeps_the_reader_on_their_line(
    review_with_a_thread_on_the_file_left: RunningReview, a_file_left_alone: Path, page: Page
) -> None:
    review = review_with_a_thread_on_the_file_left
    await page.set_viewport_size(SCREEN)
    await page.goto(review.url)
    # The reader goes to the thread, into the file read alone, and reads its line from the top of the area
    await page.get_by_test_id("outside-file").wait_for()
    await page.keyboard.press("n")
    alone = page.get_by_test_id("file-alone-view")
    read = alone.get_by_role("button", name=f"Comment on line {CHANGED_LINE}", exact=True)
    await read.evaluate(BROUGHT_TO_THE_TOP)

    # The agent's work grows the file the change touches, and retakes the diff: the file read alone is as it was
    write_files(a_file_left_alone, {ABOVE_FILE: _grown(ABOVE_FILE)})
    async with AsyncClient(base_url=review.url) as agent:
        await agent.post("/api/retake", json={})
    await page.get_by_test_id("diff-retaken").wait_for()

    await expect(read).to_be_in_viewport()


async def _reading_the_changed_line(page: Page, review: RunningReview) -> Locator:
    """The review open on a short screen, the changed line of the file the change touches read from the area's top."""
    await page.set_viewport_size(SCREEN)
    await page.goto(review.url)
    read = _section(page, ABOVE_FILE).get_by_role("button", name=f"Comment on line {CHANGED_LINE}", exact=True)
    await read.scroll_into_view_if_needed()
    await read.evaluate(BROUGHT_TO_THE_TOP)
    await page.evaluate(FRAMES_DRAWN, FRAMES_TO_SEE_THE_LINE_READ)
    return read


async def test_files_chosen_from_a_file_read_alone_show_the_reader_the_line_they_read_among_the_files(
    review_with_a_thread_on_the_file_left: RunningReview, page: Page
) -> None:
    read = await _reading_the_changed_line(page, review_with_a_thread_on_the_file_left)
    # The reader goes to the thread, into the file read alone
    await page.keyboard.press("n")
    await page.get_by_test_id("file-alone-view").wait_for()

    await page.get_by_test_id("read-as-files").click()

    await expect(read).to_be_in_viewport()


async def test_files_chosen_while_the_files_are_read_leave_the_reader_where_they_are(
    review_with_a_thread_on_the_file_left: RunningReview, page: Page
) -> None:
    read = await _reading_the_changed_line(page, review_with_a_thread_on_the_file_left)
    # The reader goes into the file read alone and back
    await page.keyboard.press("n")
    # The place left is noted for Back once the file read alone is read, which its lines say
    alone = page.get_by_test_id("file-alone-view")
    await alone.get_by_role("button", name=f"Comment on line {CHANGED_LINE}", exact=True).wait_for()
    await page.keyboard.press("b")
    await page.get_by_test_id("diff-view").wait_for()

    await page.get_by_test_id("read-as-files").click()

    await expect(page.get_by_test_id("file-alone-view")).to_have_count(0)
    await expect(read).to_be_in_viewport()


@in_the_browsers_loop
async def review_told_with_a_thread_on_the_file_left(
    review_with_a_thread_on_the_file_left: RunningReview,
) -> RunningReview:
    """The review with a thread on the file left, and a story the agent told of its change."""
    review = review_with_a_thread_on_the_file_left
    told = story_of(step(ABOVE_FILE, CHANGED_LINE, CHANGED_LINE))
    async with AsyncClient(base_url=review.url) as agent:
        (await agent.put("/api/story", json=as_the_agent_writes(told))).raise_for_status()
    return review


async def test_a_file_read_alone_the_reader_left_for_the_story_is_come_back_to_among_the_files_once_a_retake_changes_it(
    review_told_with_a_thread_on_the_file_left: RunningReview, a_file_left_alone: Path, page: Page
) -> None:
    review = review_told_with_a_thread_on_the_file_left
    await page.set_viewport_size(SCREEN)
    await page.goto(review.url)
    # The reader goes to the thread, into the file read alone, and leaves it for the story
    await page.get_by_test_id("outside-file").wait_for()
    await page.keyboard.press("n")
    await page.get_by_test_id("file-alone-view").wait_for()
    await page.get_by_test_id("read-as-story").click()
    # The agent's work changes the file read alone, and retakes the diff
    write_files(a_file_left_alone, {LEFT_FILE: _lines(LEFT_FILE, {CHANGED_LINE: "changed"})})
    async with AsyncClient(base_url=review.url) as agent:
        await agent.post("/api/retake", json={})
    await page.get_by_test_id("diff-retaken").wait_for()

    await page.get_by_test_id("read-as-files").click()

    await expect(_section(page, LEFT_FILE)).to_be_in_viewport()
    await expect(page.get_by_test_id("file-alone-view")).to_have_count(0)

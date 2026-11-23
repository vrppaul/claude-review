"""E2E: the page takes the reader to a file, and it is in view once it comes to rest.

A file's rows are built once the reader comes near it, and built they may
take more room than their section held for them: a thread under a line, a
line that wraps. So what lies below may still move after the page took the
reader there, and the page marks the file only once it has come to rest. A
reader who moves meanwhile is left where they went. Back, and the reader
choosing again a way of reading they left, take them to where they read.
Only a browser lays a page out and scrolls it.
"""

import time
from pathlib import Path

import pytest
from httpx2 import AsyncClient
from playwright.async_api import Locator, Page, expect

from claude_review.domain.models import CommentSeverity
from claude_review.domain.story import Step, Story
from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.page_reads import BROUGHT_TO_THE_TOP, FOCUSED_ELEMENT, FRAMES_DRAWN, SCROLLED
from tests.helpers import (
    ReviewServers,
    RunningReview,
    committed_repository,
    pointed_json,
    repository_opening,
    write_files,
)
from tests.stories import as_the_agent_writes, step, story_of

CHECK_ROUTE = "/api/check"
STORY_ROUTE = "/api/story"
SHOW_ROUTE = "/api/show"
POINT_ROUTE = "/api/point"
# Many screens of files, each changed in several places far apart: a hunk to
# a place, and lines left out above, between and below them
FILES_OF_MANY_HUNKS = 30
LINES_OF_EACH = 60
CHANGED_LINES = (5, 15, 25, 35, 45, 55)
PATHS = [f"file_{number:02}.py" for number in range(FILES_OF_MANY_HUNKS)]
FIRST_FILE = PATHS[0]
# Where answering round 1 changes the first file once more: what a base since that round draws
ANSWERED_AT = 2
# Far down the review, with screens of files below it still: it can be brought to the top of the area
FAR_FILE = PATHS[24]
# The file right above it, and what the agent says on its last changed line: drawn as a card under that
# line once the file is built, room its section does not hold for it
ABOVE_THE_FAR_FILE = PATHS[23]
A_THREAD_ABOVE = "Kept apart from the file below on purpose."
# The last file of the review, added with a few lines. Nothing is below it: brought as far up as the
# area scrolls, it stands at the area's foot
LAST_FILE = "zz_last.py"
THE_LAST_FILE_HOLDS = "one\ntwo\nthree\n"
# A story that tells one line of the first file and draws nothing of the last
A_STORY = story_of(step(FIRST_FILE, CHANGED_LINES[0], CHANGED_LINES[0]), housekeeping=(LAST_FILE,))
# That the page has heard the reader turn the wheel over an area, from now on: the promise of it, held in an
# object so that it is kept rather than waited for until the test reads it
HEARS_THE_WHEEL = """(area) => {
    const promise = new Promise((resolve) => area.addEventListener('wheel', () => resolve(), { once: true }));
    return { promise };
}"""
# What a promise held so comes to
KEPT = "(holding) => holding.promise"
# How far ahead of the test's clock the page's is stopped, in seconds: more than the moment the test takes to
# ask for it, which the page's clock runs through first. Stopped, it runs none of the frames its code waits for
CLOCK_HELD_FROM_SECONDS = 1
# Whether a section was marked at each move of its area from now on, in the order the area moved
MARKED_AT_EACH_MOVE = """(section) => {
    const moves = [];
    section.closest('main').addEventListener('scroll', () => moves.push(section.hasAttribute('data-marked')));
    return moves;
}"""
# How long the area is watched once the page has marked a file, in frames: a third of a second at sixty a
# second, many times the few frames the page takes to put a file right
WATCHED_FOR_FRAMES = 20
# The reading area of a browser that does not anchor its scroll: what grows above what is in view pushes it
# down. Chromium anchors it, but not where a file brought to the top lands a fraction of a pixel low, the
# file above left in view by that fraction. Where the fractions fall is a sum of every height above, so a
# test takes the anchoring away rather than look for a file that lands so
WITHOUT_SCROLL_ANCHORING = '[data-testid="diff-view"] { overflow-anchor: none; }'
# A check that failed far down the review, on a changed line of the far file, as the agent reports it
FAILED_AT = CHANGED_LINES[2]
A_CHECK_FAILED_IN_THE_FAR_FILE = {
    "name": "pytest",
    "status": "failed",
    "failures": [{"path": FAR_FILE, "line": FAILED_AT, "what": "test_far"}],
}
# How far down the files the reader has read when the page takes them away, in pixels: screens above the far file
READ_DOWN_TO = 1500
SCROLLED_DOWN_TO = "(area, offset) => { area.scrollTop = offset; }"
# A pixel of rounding, given to where the reader's turn of the wheel left the area
LESS_THAN_A_PIXEL = 1
# How far the reader turns the wheel against the page's own scroll, in pixels
A_TURN_OF_THE_WHEEL = 200
# The line of the far file the reader reads from, in the files and in the story, which leaves the far file out
READ_FROM = CHANGED_LINES[2]
# A story whose one step tells that line of the far file: screens down the files, near the head of the story
A_STORY_OF_THE_FAR_FILE = story_of(step(FAR_FILE, READ_FROM, READ_FROM))


def _lines(path: str, changed: tuple[int, ...]) -> str:
    """A file of numbered lines, those at the given numbers changed."""
    words = {number: f"{path} line {number}" for number in range(1, LINES_OF_EACH + 1)}
    words.update(dict.fromkeys(changed, f"{path} changed"))
    return "".join(f"{line}\n" for line in words.values())


@pytest.fixture
def many_hunks(tmp_path: Path) -> Path:
    """A repository whose change is several hunks in each of many files, and a short file added after them."""
    repo = committed_repository(tmp_path / "repo", {path: _lines(path, ()) for path in PATHS})
    write_files(repo, {path: _lines(path, CHANGED_LINES) for path in PATHS})
    write_files(repo, {LAST_FILE: THE_LAST_FILE_HOLDS})
    return repo


async def _told(many_hunks: Path, servers: ReviewServers, story: Story[Step]) -> RunningReview:
    """A review of the change, which the agent has told this story of."""
    started = await servers.start(await repository_opening(many_hunks))
    async with AsyncClient(base_url=started.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(story))
    return started


@in_the_browsers_loop
async def review(many_hunks: Path, servers: ReviewServers) -> RunningReview:
    """A review of the change, which the agent has told a story of."""
    return await _told(many_hunks, servers, A_STORY)


@in_the_browsers_loop
async def review_told_from_the_far_file(many_hunks: Path, servers: ReviewServers) -> RunningReview:
    """A review of the change, whose story tells a line of the far file alone."""
    return await _told(many_hunks, servers, A_STORY_OF_THE_FAR_FILE)


@in_the_browsers_loop
async def review_with_a_thread_above_the_far_file(review: RunningReview) -> RunningReview:
    """The review, with a thread the agent raised on the last changed line of the file right above the far one."""
    raised = {
        "lines": pointed_json(ABOVE_THE_FAR_FILE, CHANGED_LINES[-1]),
        "body": A_THREAD_ABOVE,
        "severity": CommentSeverity.NOTE,
    }
    async with AsyncClient(base_url=review.url) as agent:
        (await agent.post(POINT_ROUTE, json=raised)).raise_for_status()
    return review


@in_the_browsers_loop
async def review_with_a_round(many_hunks: Path, servers: ReviewServers) -> RunningReview:
    """A review whose round 1 was answered by a change to the first file alone."""
    started = await servers.start(await repository_opening(many_hunks))
    async with AsyncClient(base_url=started.url) as agent:
        await agent.post("/api/retake", json={})
        write_files(many_hunks, {FIRST_FILE: _lines(FIRST_FILE, (*CHANGED_LINES, ANSWERED_AT))})
        await agent.post("/api/retake", json={})
    return started


def _section(page: Page, path: str) -> Locator:
    return page.locator(f'[data-testid="file-section"][data-path="{path}"]')


async def _agent_shows(review: RunningReview, path: str) -> None:
    async with AsyncClient(base_url=review.url) as agent:
        await agent.post(SHOW_ROUTE, json={"file": path})


async def _marked(page: Page, path: str) -> Locator:
    """A file's section once the page has marked it: the reader has been brought to it, and it has come to rest."""
    marked = page.locator(f'[data-testid="file-section"][data-path="{path}"][data-marked]')
    await marked.wait_for()
    return marked


async def test_a_file_the_agent_shows_far_down_the_review_is_in_view_once_marked(
    review: RunningReview, page: Page
) -> None:
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')

    await _agent_shows(review, FAR_FILE)

    await expect(await _marked(page, FAR_FILE)).to_be_in_viewport()


async def test_the_reading_area_stays_where_it_is_once_a_file_the_agent_showed_is_marked(
    review_with_a_thread_above_the_far_file: RunningReview, page: Page
) -> None:
    """The mark says the reader has come to rest: the page moves them no more, though a thread's card above was drawn late."""
    await page.goto(review_with_a_thread_above_the_far_file.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    await page.add_style_tag(content=WITHOUT_SCROLL_ANCHORING)
    marked_at_each_move = await _section(page, FAR_FILE).evaluate_handle(MARKED_AT_EACH_MOVE)

    await _agent_shows(review_with_a_thread_above_the_far_file, FAR_FILE)
    await _marked(page, FAR_FILE)
    await page.evaluate(FRAMES_DRAWN, WATCHED_FOR_FRAMES)

    assert True not in await marked_at_each_move.json_value()


async def test_the_last_file_shown_while_a_story_is_read_is_marked_in_view_in_the_files(
    review: RunningReview, page: Page
) -> None:
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    await page.click('[data-testid="read-as-story"]')
    await page.wait_for_selector('[data-testid="story-piece"]')

    await _agent_shows(review, LAST_FILE)

    await expect(await _marked(page, LAST_FILE)).to_be_in_viewport()


async def test_a_reader_who_scrolls_while_the_page_takes_them_to_a_file_is_left_where_they_went(
    review: RunningReview, page: Page
) -> None:
    """The page's clock is stopped before it scrolls there, so the wheel is turned before it puts the file right."""
    await page.clock.install()
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    area = page.get_by_test_id("diff-view")
    await area.hover()
    wheel_heard = await area.evaluate_handle(HEARS_THE_WHEEL)
    await page.clock.pause_at(time.time() + CLOCK_HELD_FROM_SECONDS)

    await _agent_shows(review, FAR_FILE)
    await expect(area).not_to_have_js_property("scrollTop", 0)
    taken_to = await area.evaluate(SCROLLED)
    await page.mouse.wheel(0, -A_TURN_OF_THE_WHEEL)
    await wheel_heard.evaluate(KEPT)
    await page.clock.resume()
    await _marked(page, FAR_FILE)

    assert await area.evaluate(SCROLLED) <= taken_to - A_TURN_OF_THE_WHEEL + LESS_THAN_A_PIXEL


async def _check_failed_in_the_far_file(review: RunningReview) -> None:
    async with AsyncClient(base_url=review.url) as agent:
        (await agent.post(CHECK_ROUTE, json=A_CHECK_FAILED_IN_THE_FAR_FILE)).raise_for_status()


async def _go_to_where_the_check_failed(page: Page) -> None:
    await page.get_by_test_id("checks").click()
    await page.get_by_test_id("checks-pane").get_by_role("button", name=f"{FAR_FILE}:{FAILED_AT}").click()
    await expect(page.locator(FOCUSED_ELEMENT)).to_have_text(str(FAILED_AT))


async def _read_down_the_files(page: Page) -> Locator:
    """The files read some way down, far above the far file: the area they scroll in."""
    await page.wait_for_selector('[data-testid="file-item"]')
    area = page.get_by_test_id("diff-view")
    await area.evaluate(SCROLLED_DOWN_TO, READ_DOWN_TO)
    await page.evaluate(FRAMES_DRAWN, WATCHED_FOR_FRAMES)
    return area


async def _go_back(page: Page) -> None:
    await page.get_by_test_id("go-back").click()
    await page.evaluate(FRAMES_DRAWN, WATCHED_FOR_FRAMES)


async def test_back_from_where_a_check_failed_shows_the_reader_what_they_were_reading(
    review: RunningReview, page: Page
) -> None:
    await _check_failed_in_the_far_file(review)
    await page.goto(review.url)
    area = await _read_down_the_files(page)
    read_at = await area.evaluate(SCROLLED)
    await _go_to_where_the_check_failed(page)

    await _go_back(page)

    assert abs(await area.evaluate(SCROLLED) - read_at) < LESS_THAN_A_PIXEL


async def test_going_again_to_a_line_in_sight_leaves_no_way_back_to_it(review: RunningReview, page: Page) -> None:
    await _check_failed_in_the_far_file(review)
    await page.goto(review.url)
    await _read_down_the_files(page)
    await _go_to_where_the_check_failed(page)

    await _go_to_where_the_check_failed(page)
    await _go_back(page)

    await expect(page.get_by_test_id("go-back")).to_have_count(0)


async def test_back_from_a_jump_out_of_a_narrower_base_takes_the_reader_to_the_file_they_read(
    review_with_a_round: RunningReview, page: Page
) -> None:
    """The jump puts the whole review back, as the narrower base draws no line of the far file."""
    await _check_failed_in_the_far_file(review_with_a_round)
    await page.goto(review_with_a_round.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    await page.click('[data-testid="base-picker"]')
    await page.get_by_test_id("base-option").filter(has_text="round 1").click()
    await page.wait_for_selector('[data-testid="narrowed-to"]')
    await _go_to_where_the_check_failed(page)

    await _go_back(page)

    await expect(_section(page, FIRST_FILE).locator(FOCUSED_ELEMENT)).to_have_count(1)


async def test_back_from_a_jump_off_the_storys_words_brings_the_story_back_as_the_reader_left_it(
    review: RunningReview, page: Page
) -> None:
    await _check_failed_in_the_far_file(review)
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    await page.click('[data-testid="read-as-story"]')
    await page.wait_for_selector('[data-testid="story-piece"]')
    await _go_to_where_the_check_failed(page)

    await _go_back(page)

    await expect(page.get_by_test_id("story-view")).to_have_js_property("scrollTop", 0)


async def _read_from_its_line(page: Page, section: Locator) -> Locator:
    """The far file read in a section from its line, brought to the top of the area: the line, once the page sees it read."""
    await section.evaluate(BROUGHT_TO_THE_TOP)
    line = section.get_by_role("button", name=f"Comment on line {READ_FROM}", exact=True)
    await line.evaluate(BROUGHT_TO_THE_TOP)
    await page.evaluate(FRAMES_DRAWN, WATCHED_FOR_FRAMES)
    return line


async def _choose(page: Page, view: str) -> None:
    await page.get_by_test_id(view).click()
    await page.evaluate(FRAMES_DRAWN, WATCHED_FOR_FRAMES)


async def test_files_chosen_again_after_the_story_show_the_reader_the_line_they_read_the_keyboard_left_on_files(
    review: RunningReview, page: Page
) -> None:
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    line = await _read_from_its_line(page, _section(page, FAR_FILE))
    await _choose(page, "read-as-story")

    await _choose(page, "read-as-files")

    await expect(line).to_be_in_viewport()
    await expect(page.get_by_test_id("read-as-files")).to_be_focused()


async def test_the_story_chosen_again_after_the_files_shows_the_reader_the_line_they_read(
    review: RunningReview, page: Page
) -> None:
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    await _choose(page, "read-as-story")
    piece = page.locator(f'[data-testid="story-piece"][data-path="{FAR_FILE}"]')
    line = await _read_from_its_line(page, piece)
    await _choose(page, "read-as-files")

    await _choose(page, "read-as-story")

    await expect(line).to_be_in_viewport()


async def _open_the_steps_file(page: Page) -> None:
    """Read the review as its story, and press the step's way to its file among the change's files."""
    await page.click('[data-testid="read-as-story"]')
    await page.get_by_test_id("step-open-in-files").click()
    await page.evaluate(FRAMES_DRAWN, WATCHED_FOR_FRAMES)


async def test_a_steps_file_opened_from_the_story_shows_the_reader_the_steps_first_line_among_the_files(
    review_told_from_the_far_file: RunningReview, page: Page
) -> None:
    await page.goto(review_told_from_the_far_file.url)
    await page.wait_for_selector('[data-testid="file-item"]')

    await _open_the_steps_file(page)

    line = _section(page, FAR_FILE).get_by_role("button", name=f"Comment on line {READ_FROM}", exact=True)
    await expect(line).to_be_in_viewport()


async def test_back_from_a_steps_file_brings_the_story_back_at_the_step(
    review_told_from_the_far_file: RunningReview, page: Page
) -> None:
    await page.goto(review_told_from_the_far_file.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    await _open_the_steps_file(page)

    await page.keyboard.press("b")

    line = page.get_by_test_id("step-frame").get_by_role("button", name=f"Comment on line {READ_FROM}", exact=True)
    await expect(line).to_be_in_viewport()

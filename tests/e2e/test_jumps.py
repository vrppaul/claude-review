"""E2E: the page takes the reader to a file, and it is in view once it comes to rest.

A file's rows are built once the reader comes near it, and built they may
take more room than their section held for them: a thread under a line, a
line that wraps. So what lies below may still move after the page took the
reader there, and the page marks the file only once it has come to rest. A
reader who moves meanwhile is left where they went. Only a browser lays a
page out and scrolls it.
"""

import time
from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Locator, Page, expect

from claude_review.domain.models import CommentSeverity
from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.page_reads import SCROLLED
from tests.helpers import (
    ReviewServers,
    RunningReview,
    committed_repository,
    line_on_the_wire,
    repository_opening,
    write_files,
)
from tests.stories import as_the_agent_writes, step, story_of

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
# Let the page draw a number of frames
FRAMES_DRAWN = (
    "async (count) => { for (let frame = 0; frame < count; frame += 1) await new Promise(requestAnimationFrame); }"
)
# How long the area is watched once the page has marked a file, in frames: a third of a second at sixty a
# second, many times the few frames the page takes to put a file right
WATCHED_FOR_FRAMES = 20
# The reading area of a browser that does not anchor its scroll: what grows above what is in view pushes it
# down. Chromium anchors it, but not where a file brought to the top lands a fraction of a pixel low, the
# file above left in view by that fraction. Where the fractions fall is a sum of every height above, so a
# test takes the anchoring away rather than look for a file that lands so
WITHOUT_SCROLL_ANCHORING = '[data-testid="diff-view"] { overflow-anchor: none; }'
# A pixel of rounding, given to where the reader's turn of the wheel left the area
LESS_THAN_A_PIXEL = 1
# How far the reader turns the wheel against the page's own scroll, in pixels
A_TURN_OF_THE_WHEEL = 200


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


@in_the_browsers_loop
async def review(many_hunks: Path, servers: ReviewServers) -> RunningReview:
    """A review of the change, which the agent has told a story of."""
    started = await servers.start(await repository_opening(many_hunks))
    async with AsyncClient(base_url=started.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(A_STORY))
    return started


@in_the_browsers_loop
async def review_with_a_thread_above_the_far_file(review: RunningReview) -> RunningReview:
    """The review, with a thread the agent raised on the last changed line of the file right above the far one."""
    raised = {
        "anchor": line_on_the_wire(ABOVE_THE_FAR_FILE, CHANGED_LINES[-1]),
        "body": A_THREAD_ABOVE,
        "severity": CommentSeverity.NOTE,
    }
    async with AsyncClient(base_url=review.url) as agent:
        (await agent.post(POINT_ROUTE, json=raised)).raise_for_status()
    return review


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

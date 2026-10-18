"""E2E: the page takes the reader to a file at once, and the file is where it took them.

A file's rows are built once the reader comes near it; until then its
section holds the room they are counted to take: its rows, the header of
each hunk and the bar for the lines left out around it. Built, a file takes
more only for what is not counted, a thread under a line or a line that
wraps, so what lies below may still move while the files around it are
built, after the page took the reader there. Only a browser lays a page out
and scrolls it.
"""

import time
from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Locator, Page, expect

from claude_review.domain.models import CommentSeverity
from tests.e2e.browsers_loop import in_the_browsers_loop
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
# The file after the first, about a screen down the review
NEAR_FILE = PATHS[1]
# The last file of the review, added with a few lines. Nothing is below it: brought as far up as the
# area scrolls, it stands at the area's foot
LAST_FILE = "zz_last.py"
THE_LAST_FILE_HOLDS = "one\ntwo\nthree\n"
# A story that tells one line of the first file and draws nothing of the last
A_STORY = story_of(step(FIRST_FILE, CHANGED_LINES[0], CHANGED_LINES[0]), housekeeping=(LAST_FILE,))
# How far below the top of the area it scrolls in a section's head stands, in pixels
BELOW_THE_AREAS_TOP = """(section) => {
    const area = section.closest('main');
    return section.getBoundingClientRect().top - area.getBoundingClientRect().top;
}"""
# How far below the top of the area a section's head stands the first time the area moves from now on: the
# promise of it, held in an object so that it is kept rather than waited for until the test reads it
AT_THE_FIRST_MOVE = """(section) => {
    const area = section.closest('main');
    const promise = new Promise((resolve) => area.addEventListener(
        'scroll',
        () => resolve(section.getBoundingClientRect().top - area.getBoundingClientRect().top),
        { once: true }
    ));
    return { promise };
}"""
# That the page has heard the reader turn the wheel over an area, from now on: its promise held the same way
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
# A fraction of a pixel: where a head stands is not a whole number, and the area scrolls by whole ones
LESS_THAN_A_PIXEL = 1
# How tall a section stands on the page
HEIGHT = "(section) => section.getBoundingClientRect().height"
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


def _piece(page: Page, path: str) -> Locator:
    return page.locator(f'[data-testid="story-piece"][data-path="{path}"]')


async def _grown_once_built(section: Locator) -> float:
    """How much taller a section whose rows are not built yet stands once they are: brought into view, they are."""
    placeholder = section.get_by_test_id("file-placeholder")
    await placeholder.wait_for(state="attached")
    held = await section.evaluate(HEIGHT)
    await section.scroll_into_view_if_needed()
    await placeholder.wait_for(state="detached")
    return await section.evaluate(HEIGHT) - held


async def _marked(page: Page, path: str) -> Locator:
    """A file's section once the page has marked it: the reader has been brought to it, and it has come to rest."""
    marked = page.locator(f'[data-testid="file-section"][data-path="{path}"][data-marked]')
    await marked.wait_for()
    return marked


async def test_a_file_far_down_the_review_holds_the_room_its_hunks_take_before_they_are_built(
    review: RunningReview, page: Page
) -> None:
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')

    assert abs(await _grown_once_built(_section(page, FAR_FILE))) < LESS_THAN_A_PIXEL


async def test_a_file_laid_out_in_two_columns_holds_the_room_its_rows_take_before_they_are_built(
    review: RunningReview, page: Page
) -> None:
    await page.goto(review.url)
    await page.get_by_test_id("settings-toggle").click()
    await page.get_by_test_id("layout-split").click()
    await _section(page, FIRST_FILE).get_by_test_id("split-view").wait_for()

    assert abs(await _grown_once_built(_section(page, FAR_FILE))) < LESS_THAN_A_PIXEL


async def test_a_piece_far_down_a_story_holds_the_room_its_hunks_take_before_they_are_built(
    review: RunningReview, page: Page
) -> None:
    """Of a file no step tells, the story draws what it changes: a piece of several hunks, the lines between said."""
    await page.goto(review.url)
    await page.click('[data-testid="read-as-story"]')
    await page.wait_for_selector('[data-testid="story-piece"]')

    assert abs(await _grown_once_built(_piece(page, FAR_FILE))) < LESS_THAN_A_PIXEL


async def test_a_file_the_agent_shows_far_down_the_review_is_marked_at_the_top_of_the_reading_area(
    review: RunningReview, page: Page
) -> None:
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')

    await _agent_shows(review, FAR_FILE)
    shown = await _marked(page, FAR_FILE)

    assert abs(await shown.evaluate(BELOW_THE_AREAS_TOP)) < LESS_THAN_A_PIXEL


@pytest.mark.parametrize("path", [NEAR_FILE, FAR_FILE])
async def test_a_file_the_agent_shows_is_at_the_top_of_the_reading_area_from_the_first_frame_the_area_moves_in(
    review: RunningReview, page: Page, path: str
) -> None:
    """Taken there at once, a screen down or many: a glide would have it still on its way, below."""
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    first_move = await _section(page, path).evaluate_handle(AT_THE_FIRST_MOVE)

    await _agent_shows(review, path)

    assert abs(await first_move.evaluate(KEPT)) < LESS_THAN_A_PIXEL


async def test_a_file_the_agent_shows_far_down_under_a_file_that_holds_a_thread_is_marked_at_the_top_of_the_reading_area(
    review_with_a_thread_above_the_far_file: RunningReview, page: Page
) -> None:
    """The card is drawn as the file above is built, after the page took the reader there, and pushes the file down."""
    await page.goto(review_with_a_thread_above_the_far_file.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    await page.add_style_tag(content=WITHOUT_SCROLL_ANCHORING)

    await _agent_shows(review_with_a_thread_above_the_far_file, FAR_FILE)
    shown = await _marked(page, FAR_FILE)

    assert abs(await shown.evaluate(BELOW_THE_AREAS_TOP)) < LESS_THAN_A_PIXEL


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
    shown = await _marked(page, LAST_FILE)

    area_height = await page.get_by_test_id("diff-view").evaluate("(area) => area.clientHeight")
    assert 0 <= await shown.evaluate(BELOW_THE_AREAS_TOP) < area_height


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
    await page.mouse.wheel(0, -A_TURN_OF_THE_WHEEL)
    await wheel_heard.evaluate(KEPT)
    await page.clock.resume()
    shown = await _marked(page, FAR_FILE)

    assert await shown.evaluate(BELOW_THE_AREAS_TOP) >= A_TURN_OF_THE_WHEEL - LESS_THAN_A_PIXEL

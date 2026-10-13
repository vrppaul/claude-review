"""E2E: the page itself never scrolls; whatever is long scrolls in an area of its own.

The header, the tree, the reading area and the panel each hold their place
on the screen, and a long tree or a long story scrolls inside its own area.
Words kept for a screen reader are taken out of the flow: in an area that
is not the box its contents are placed in, they stay where they were first
put while the rest scrolls — far down a page that then grows to hold them,
scrolls itself, and takes the header off the screen at the next jump. Only
a browser lays a page out, so only here can that be seen.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Page, expect

from tests.helpers import ReviewServers, RunningReview, committed_repository, repository_opening, write_files
from tests.stories import as_the_agent_writes, step, story_of

STORY_ROUTE = "/api/story"
# More files than a tree shows on one screen, each short, and more steps than a story shows on one
MANY_FILES = 60
LINES_OF_EACH = 12
FILES = {
    f"file_{number:02}.py": "".join(f"line {line}\n" for line in range(1, LINES_OF_EACH + 1))
    for number in range(MANY_FILES)
}
LAST_FILE = f"file_{MANY_FILES - 1:02}.py"
# A story that tells every file whole, a step each
A_LONG_STORY = story_of(*(step(file, 1, LINES_OF_EACH) for file in FILES))
# How far the page itself has scrolled, and how much taller than its window the document is
PAGE_SCROLLED_BY = "() => window.scrollY"
TALLER_THAN_THE_WINDOW_BY = "() => document.documentElement.scrollHeight - window.innerHeight"
# How many times the reader steps to the next piece of the story
STEPS_DOWN_THE_STORY = 5


@pytest.fixture
async def review_of_many_files(tmp_path: Path, servers: ReviewServers) -> RunningReview:
    """A review of more added files than fit on a screen, which the agent has told a story of, a step to a file."""
    repository = committed_repository(tmp_path / "repo", {"README.md": "# Many files\n"})
    write_files(repository, FILES)
    started = await servers.start(await repository_opening(repository))
    async with AsyncClient(base_url=started.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(A_LONG_STORY))
    return started


async def test_a_file_picked_at_the_foot_of_a_long_tree_leaves_the_page_where_it_is(
    review_of_many_files: RunningReview, page: Page
) -> None:
    await page.goto(review_of_many_files.url)
    await page.wait_for_selector('[data-testid="file-item"]')

    await page.get_by_test_id("file-item").filter(has_text=LAST_FILE).click()
    await page.locator(f'[data-testid="file-section"][data-path="{LAST_FILE}"]').get_by_test_id("raw-view").wait_for()

    assert await page.evaluate(TALLER_THAN_THE_WINDOW_BY) == 0
    assert await page.evaluate(PAGE_SCROLLED_BY) == 0


async def test_stepping_down_a_long_story_leaves_the_page_where_it_is(
    review_of_many_files: RunningReview, page: Page
) -> None:
    await page.goto(review_of_many_files.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    await page.click('[data-testid="read-as-story"]')
    await page.wait_for_selector('[data-testid="story-piece"]')

    for _ in range(STEPS_DOWN_THE_STORY):
        await page.keyboard.press("]")

    assert await page.evaluate(TALLER_THAN_THE_WINDOW_BY) == 0
    assert await page.evaluate(PAGE_SCROLLED_BY) == 0


async def test_a_file_picked_at_the_foot_of_a_story_s_long_contents_leaves_the_page_where_it_is(
    review_of_many_files: RunningReview, page: Page
) -> None:
    await page.goto(review_of_many_files.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    await page.click('[data-testid="read-as-story"]')
    await page.wait_for_selector('[data-testid="story-piece"]')

    await page.get_by_test_id("contents-file").filter(has_text=LAST_FILE).click()
    await expect(page.get_by_test_id("story-piece").last).to_be_in_viewport()

    assert await page.evaluate(TALLER_THAN_THE_WINDOW_BY) == 0
    assert await page.evaluate(PAGE_SCROLLED_BY) == 0

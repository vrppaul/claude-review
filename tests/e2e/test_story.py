"""E2E: a review read as the story the agent told of it, in a real browser.

A story is the same review read another way: its steps take comments that
hang on the file's own lines, and what it does not draw is one press away
in the files, with the keyboard on it. When the diff is taken again under
it, the story shows code that has moved on, says so, and takes nothing.
Where the keyboard lands, and what a key does to what is not on screen,
are only true in a browser.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Locator, Page, ViewportSize, expect

from claude_review.domain.story import ToldFrom
from tests.helpers import ReviewServers, RunningReview, committed_repository, repository_opening, write_files
from tests.stories import ONLY_CHAPTER, as_the_agent_writes, chapter_of, step, story_of, story_of_chapters

STORY_ROUTE = "/api/story"
RETAKE_ROUTE = "/api/retake"

TOLD_FILE = "told.py"
HOUSEKEEPING_FILE = "notes.txt"
COMMITTED_FILES = {TOLD_FILE: "keep one\nfirst two\nkeep three\n", HOUSEKEEPING_FILE: "a note\n"}
# The change under review: line 2 of the file the story tells, and a line of the file it names as housekeeping
THE_CHANGE = {TOLD_FILE: "keep one\nchanged two\nkeep three\n", HOUSEKEEPING_FILE: "another note\n"}
# The told file as a round's work leaves it: two lines above the one the story told
MOVED_ON = {TOLD_FILE: "new first\nnew second\nkeep one\nchanged two\nkeep three\n"}
# The line the story's one step tells, as the step's piece numbers it
TOLD_LINE = "Comment on line 2"
# The line the housekeeping file gained, which no piece of the story draws
CHANGED_NOTE = "Comment on line 1"
A_STORY = story_of(step(TOLD_FILE, 2, 2), housekeeping=(HOUSEKEEPING_FILE,))
# The same change told by an agent that did not make it, from its commits
A_RECONSTRUCTION = story_of_chapters(
    chapter_of(ONLY_CHAPTER, step(TOLD_FILE, 2, 2)), housekeeping=(HOUSEKEEPING_FILE,), told_from=ToldFrom.COMMITS
)
# The edge down the left of a block, as the browser draws it: how it is drawn, how wide, and in what colour
EDGE_STYLE = "(element) => getComputedStyle(element).borderLeftStyle"
EDGE_WIDTH = "(element) => getComputedStyle(element).borderLeftWidth"
EDGE_COLOUR = "(element) => getComputedStyle(element).borderLeftColor"
# The colour an element's words are drawn in
WORDS_COLOUR = "(element) => getComputedStyle(element).color"
# How wide the agent's edge is drawn
AGENT_EDGE_WIDTH = "2px"
# A file added whole, long enough that its piece runs far past the bottom of the screen
LONG_FILE = "long.py"
LINES_OF_THE_LONG_FILE = 200
# How far into the long piece the reader scrolls: well past its head, well short of its end
DEEP_IN_THE_PIECE = 1500
# Where an element's top edge is on screen, in pixels from the top of the window
TOP_OF = "(element) => element.getBoundingClientRect().top"
# And its bottom edge
BOTTOM_OF = "(element) => element.getBoundingClientRect().bottom"
# Where an element's right edge is, in pixels from the left of the window, and where what it holds must end: its padding short of that
RIGHT_OF = "(element) => element.getBoundingClientRect().right"
RIGHT_INSIDE_ITS_PADDING = (
    "(element) => element.getBoundingClientRect().right - parseFloat(getComputedStyle(element).paddingRight)"
)
# How wide an element is on screen, and how wide the window it is drawn in
WIDTH_OF = "(element) => element.getBoundingClientRect().width"
WINDOW_WIDTH = "window.innerWidth"
# Wide enough for the tree of files to stand beside them
WIDE_SCREEN: ViewportSize = {"width": 1600, "height": 900}


@pytest.fixture
def changed_repo(tmp_path: Path) -> Path:
    """A repository with a change to tell a story of."""
    repo = committed_repository(tmp_path / "repo", COMMITTED_FILES)
    write_files(repo, THE_CHANGE)
    return repo


@pytest.fixture
async def review(changed_repo: Path, servers: ReviewServers) -> RunningReview:
    """A review of the change, which the agent has told a story of."""
    started = await servers.start(await repository_opening(changed_repo))
    async with AsyncClient(base_url=started.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(A_STORY))
    return started


@pytest.fixture
async def review_of_a_reconstruction(changed_repo: Path, servers: ReviewServers) -> RunningReview:
    """A review of the change, whose story an agent that did not make it told from the commits."""
    started = await servers.start(await repository_opening(changed_repo))
    async with AsyncClient(base_url=started.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(A_RECONSTRUCTION))
    return started


@pytest.fixture
def long_file_repo(tmp_path: Path) -> Path:
    """A repository whose change adds one file whole, longer than any screen."""
    repo = committed_repository(tmp_path / "long", COMMITTED_FILES)
    write_files(repo, {LONG_FILE: "".join(f"line {number}\n" for number in range(1, LINES_OF_THE_LONG_FILE + 1))})
    return repo


@pytest.fixture
async def review_of_a_long_file(long_file_repo: Path, servers: ReviewServers) -> RunningReview:
    """A review whose story tells, in one step, the file its change adds whole."""
    started = await servers.start(await repository_opening(long_file_repo))
    async with AsyncClient(base_url=started.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(story_of(step(LONG_FILE, 1, LINES_OF_THE_LONG_FILE))))
    return started


async def _read_as_story(page: Page, review: RunningReview) -> None:
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    await page.click('[data-testid="read-as-story"]')
    await page.wait_for_selector('[data-testid="story-piece"]')


async def _comment_on(page: Page, drawn_in: Locator, line: str, words: str) -> None:
    """Write a comment on a line, by its number, in the one part of the page that draws the line."""
    await drawn_in.get_by_role("button", name=line, exact=True).click()
    await page.fill('[data-testid="comment-input"]', words)
    await page.click('[data-testid="save-comment"]')
    await page.wait_for_selector('[data-testid="comment-thread"]')


async def test_a_comment_written_on_a_step_hangs_on_the_same_line_of_the_file(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review)

    await _comment_on(page, page.get_by_test_id("story-piece"), TOLD_LINE, "why this word")
    await page.click('[data-testid="read-as-files"]')

    in_the_files = page.get_by_test_id("file-section").filter(has_text=TOLD_FILE)
    await expect(in_the_files.get_by_test_id("comment-thread")).to_contain_text("why this word")


async def _read_as_story_with_a_comment_it_does_not_draw(page: Page, review: RunningReview) -> None:
    """Comment in the files on the housekeeping file, which no piece of the story draws, then read the story."""
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    the_note = page.get_by_test_id("file-section").filter(has_text=HOUSEKEEPING_FILE)
    await _comment_on(page, the_note, CHANGED_NOTE, "about the note")
    await page.click('[data-testid="read-as-story"]')


async def test_the_way_to_a_comment_the_story_does_not_draw_puts_the_keyboard_on_it(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story_with_a_comment_it_does_not_draw(page, review)

    await page.click('[data-testid="show-in-files"]')
    await page.wait_for_selector('[data-testid="diff-view"]')

    await expect(page.locator('[data-testid="comment-thread"]:focus')).to_contain_text("about the note")


async def test_what_a_story_says_of_itself_stands_across_the_page_right_above_what_is_read(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story_with_a_comment_it_does_not_draw(page, review)
    said = page.get_by_test_id("threads-off-the-story")
    await said.wait_for()

    assert await said.evaluate(WIDTH_OF) == await page.evaluate(WINDOW_WIDTH)
    assert await said.evaluate(BOTTOM_OF) == await page.get_by_test_id("story-view").evaluate(TOP_OF)


async def test_the_way_to_what_a_story_does_not_draw_stands_at_the_far_end_of_what_it_says(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story_with_a_comment_it_does_not_draw(page, review)
    said = page.get_by_test_id("threads-off-the-story")
    await said.wait_for()

    the_way = said.get_by_test_id("show-in-files")
    assert await the_way.evaluate(RIGHT_OF) == await said.evaluate(RIGHT_INSIDE_ITS_PADDING)


async def test_a_story_the_code_has_moved_on_from_says_so_and_takes_no_comment(
    review: RunningReview, changed_repo: Path, page: Page
) -> None:
    await _read_as_story(page, review)

    write_files(changed_repo, MOVED_ON)
    async with AsyncClient(base_url=review.url) as agent:
        await agent.post(RETAKE_ROUTE, json={})

    await expect(page.get_by_test_id("story-moved-on")).to_contain_text(
        "The code has changed since this story was told."
    )
    told_line = page.get_by_test_id("story-piece").get_by_role("button", name=TOLD_LINE, exact=True)
    await expect(told_line).to_have_attribute("aria-disabled", "true")
    # By the keyboard, which reaches a number that takes no comment: a pointer's press waits for one that does
    await told_line.focus()
    await page.keyboard.press("Enter")
    await expect(page.get_by_test_id("comment-input")).to_have_count(0)


async def test_deep_in_a_story_the_code_has_moved_on_from_the_page_still_says_so(
    review_of_a_long_file: RunningReview, long_file_repo: Path, page: Page
) -> None:
    await _read_as_story(page, review_of_a_long_file)
    write_files(long_file_repo, {LONG_FILE: "a line above them all\n"})
    async with AsyncClient(base_url=review_of_a_long_file.url) as agent:
        await agent.post(RETAKE_ROUTE, json={})
    moved_on = page.get_by_test_id("story-moved-on")
    await moved_on.wait_for()

    await page.get_by_test_id("story-view").evaluate("(area, depth) => area.scrollBy(0, depth)", DEEP_IN_THE_PIECE)

    await expect(moved_on).to_be_in_viewport()


async def test_f_in_the_story_leaves_the_tree_of_files_where_the_reader_left_it(
    review: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(WIDE_SCREEN)
    await _read_as_story(page, review)

    await page.keyboard.press("f")
    await page.click('[data-testid="read-as-files"]')

    await expect(page.get_by_test_id("file-item").first).to_be_visible()


async def test_the_agents_words_carry_its_colour_down_their_edge_and_a_reconstruction_a_broken_one(
    review_of_a_reconstruction: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review_of_a_reconstruction)
    why = page.get_by_test_id("chapter-why")
    reconstruction = page.get_by_test_id("story-reconstruction")
    the_agents_colour = await page.get_by_test_id("story-reconstructed").evaluate(WORDS_COLOUR)

    assert await why.evaluate(EDGE_STYLE) == "solid"
    assert await why.evaluate(EDGE_WIDTH) == AGENT_EDGE_WIDTH
    assert await why.evaluate(EDGE_COLOUR) == the_agents_colour
    assert await reconstruction.evaluate(EDGE_STYLE) == "dashed"
    assert await reconstruction.evaluate(EDGE_WIDTH) == AGENT_EDGE_WIDTH
    assert await reconstruction.evaluate(EDGE_COLOUR) == the_agents_colour


async def test_deep_in_a_long_piece_its_header_stays_in_view_saying_which_file_is_read(
    review_of_a_long_file: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review_of_a_long_file)
    story = page.get_by_test_id("story-view")

    await story.evaluate("(area, depth) => area.scrollBy(0, depth)", DEEP_IN_THE_PIECE)

    header = page.get_by_test_id("story-piece-header")
    await expect(header).to_be_in_viewport()
    assert await header.evaluate(TOP_OF) == await story.evaluate(TOP_OF)

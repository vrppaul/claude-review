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

from claude_review.domain.models import LineSpan
from claude_review.domain.story import Step, ToldFrom
from tests.e2e.browsers_loop import in_the_browsers_loop
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
# The long file told in two steps, each longer than a screen: the last line the first of them tells,
# and why the second is as it is, said above its piece
LAST_LINE_OF_THE_FIRST_STEP = 100
REASON_OF_THE_SECOND_STEP = "The second half of the file goes on from the first."
THE_LONG_FILE_IN_TWO_STEPS = story_of(
    step(LONG_FILE, 1, LAST_LINE_OF_THE_FIRST_STEP),
    Step(
        file=LONG_FILE,
        lines=LineSpan(first=LAST_LINE_OF_THE_FIRST_STEP + 1, last=LINES_OF_THE_LONG_FILE),
        reason=REASON_OF_THE_SECOND_STEP,
    ),
)
# The same two steps as a chapter each: the long file is then told in two chapters, and the contents
# list it under both
SECOND_CHAPTER = "ch-2"
THE_LONG_FILE_IN_TWO_CHAPTERS = story_of_chapters(
    chapter_of(ONLY_CHAPTER, step(LONG_FILE, 1, LAST_LINE_OF_THE_FIRST_STEP)),
    chapter_of(
        SECOND_CHAPTER,
        Step(
            file=LONG_FILE,
            lines=LineSpan(first=LAST_LINE_OF_THE_FIRST_STEP + 1, last=LINES_OF_THE_LONG_FILE),
            reason=REASON_OF_THE_SECOND_STEP,
        ),
    ),
)
# The first line the second of those chapters tells, as its piece numbers it
FIRST_LINE_OF_THE_SECOND_CHAPTER = f"Comment on line {LAST_LINE_OF_THE_FIRST_STEP + 1}"
# A fraction of a pixel: where an edge stands is not a whole number, and the area scrolls by whole ones
LESS_THAN_A_PIXEL = 1
# How tall everything an area scrolls is, in pixels, and how far down it has scrolled
HEIGHT_HELD = "(area) => area.scrollHeight"
SCROLLED = "(area) => area.scrollTop"
# The keys that step a line down and up
LINE_KEYS = ("j", "k")
# How far under the foot of its piece's header the line that holds the keyboard begins, in heights of a
# line: under 0 the header is drawn over it, and from 1 on a line above it is in sight too
LINES_UNDER_ITS_HEADER = """() => {
    const line = document.activeElement;
    const header = line.closest('[data-testid="story-piece"]').querySelector('[data-testid="story-piece-header"]');
    const under = line.getBoundingClientRect().top - header.getBoundingClientRect().bottom;
    return under / line.getBoundingClientRect().height;
}"""
# A fraction of a line: where an edge stands is not a whole number of pixels
LESS_THAN_A_LINE_APART = 0.05
# A wide screen zoomed in: too narrow for a column to stand beside what is read
ZOOMED: ViewportSize = {"width": 640, "height": 400}
# Where an element's left edge is, in pixels from the left of the window
LEFT_OF = "(element) => element.getBoundingClientRect().left"
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
# What the head of the contents says of a story of two chapters: with neither read through, and with one
TWO_CHAPTERS = "2 chapters"
ONE_OF_TWO_READ = "1 of 2 read"
# Bring an element to the middle of the area it scrolls in, at once
TO_THE_MIDDLE = "(element) => element.scrollIntoView({ block: 'center' })"
# How strongly an element is drawn, and the strength of one that has not stepped back
OPACITY_OF = "(element) => Number(getComputedStyle(element).opacity)"
FULLY_DRAWN = 1
# Whether nothing on the page holds the keyboard, and what does, by the test id it carries
KEYBOARD_ON_NOTHING = "document.activeElement === document.body"
HOLDS_THE_KEYBOARD = "document.activeElement?.dataset.testid"
# How wide a story's contents stand, in pixels, until the reader sizes them
CONTENTS_WIDTH_AT_FIRST = 260


@pytest.fixture
def changed_repo(tmp_path: Path) -> Path:
    """A repository with a change to tell a story of."""
    repo = committed_repository(tmp_path / "repo", COMMITTED_FILES)
    write_files(repo, THE_CHANGE)
    return repo


@in_the_browsers_loop
async def review(changed_repo: Path, servers: ReviewServers) -> RunningReview:
    """A review of the change, which the agent has told a story of."""
    started = await servers.start(await repository_opening(changed_repo))
    async with AsyncClient(base_url=started.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(A_STORY))
    return started


@in_the_browsers_loop
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


@in_the_browsers_loop
async def review_of_a_long_file(long_file_repo: Path, servers: ReviewServers) -> RunningReview:
    """A review whose story tells, in one step, the file its change adds whole."""
    started = await servers.start(await repository_opening(long_file_repo))
    async with AsyncClient(base_url=started.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(story_of(step(LONG_FILE, 1, LINES_OF_THE_LONG_FILE))))
    return started


@in_the_browsers_loop
async def review_of_a_long_file_in_two_steps(long_file_repo: Path, servers: ReviewServers) -> RunningReview:
    """A review whose story tells the file its change adds in two steps, the second with its reason."""
    started = await servers.start(await repository_opening(long_file_repo))
    async with AsyncClient(base_url=started.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(THE_LONG_FILE_IN_TWO_STEPS))
    return started


@in_the_browsers_loop
async def review_of_a_long_file_in_two_chapters(long_file_repo: Path, servers: ReviewServers) -> RunningReview:
    """A review whose story tells the file its change adds in two chapters, a step each."""
    started = await servers.start(await repository_opening(long_file_repo))
    async with AsyncClient(base_url=started.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(THE_LONG_FILE_IN_TWO_CHAPTERS))
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


async def _below_the_bar(page: Page, drawn: Locator) -> float:
    """How far under the bar of the chapter being read the top of something stands, in pixels."""
    return await drawn.evaluate(TOP_OF) - await page.get_by_test_id("chapter-bar").evaluate(BOTTOM_OF)


async def test_deep_in_a_chapter_its_bar_stands_at_the_top_of_what_is_read_and_takes_no_room_of_the_story(
    review_of_a_long_file: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review_of_a_long_file)
    story = page.get_by_test_id("story-view")
    held_without_the_bar = await story.evaluate(HEIGHT_HELD)

    await story.evaluate("(area, depth) => area.scrollBy(0, depth)", DEEP_IN_THE_PIECE)

    bar = page.get_by_test_id("chapter-bar")
    await expect(bar).to_be_in_viewport()
    assert await bar.evaluate(TOP_OF) == await story.evaluate(TOP_OF)
    assert await story.evaluate(HEIGHT_HELD) == held_without_the_bar


async def test_deep_in_a_long_piece_its_header_stays_in_view_right_under_the_bar_of_its_chapter(
    review_of_a_long_file: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review_of_a_long_file)
    story = page.get_by_test_id("story-view")

    await story.evaluate("(area, depth) => area.scrollBy(0, depth)", DEEP_IN_THE_PIECE)

    header = page.get_by_test_id("story-piece-header")
    await expect(header).to_be_in_viewport()
    assert abs(await _below_the_bar(page, header)) < LESS_THAN_A_PIXEL


@pytest.mark.parametrize("line_key", LINE_KEYS)
async def test_a_line_key_deep_in_a_chapter_lands_on_the_first_line_in_sight_under_its_bar_and_the_header_of_its_piece(
    review_of_a_long_file: RunningReview, page: Page, line_key: str
) -> None:
    """Scrolled by hand, the keyboard is still on the switch in the header: the key starts at the first line the reader sees."""
    await _read_as_story(page, review_of_a_long_file)
    story = page.get_by_test_id("story-view")
    await story.evaluate("(area, depth) => area.scrollBy(0, depth)", DEEP_IN_THE_PIECE)
    await expect(page.get_by_test_id("chapter-bar")).to_be_in_viewport()

    await page.keyboard.press(line_key)

    assert await page.evaluate(HOLDS_THE_KEYBOARD) == "line-gutter"
    assert -LESS_THAN_A_LINE_APART <= await page.evaluate(LINES_UNDER_ITS_HEADER) < 1
    assert await story.evaluate(SCROLLED) == DEEP_IN_THE_PIECE


async def test_a_step_gone_to_stands_right_under_the_bar_of_its_chapter_from_its_reason_down(
    review_of_a_long_file_in_two_steps: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review_of_a_long_file_in_two_steps)

    # Twice, so the reader ends on the second step wherever the first press took them from: ] goes no further than the last
    await page.keyboard.press("]")
    await page.keyboard.press("]")

    reason = page.get_by_test_id("step-reason")
    await expect(reason).to_be_in_viewport()
    assert abs(await _below_the_bar(page, reason)) < LESS_THAN_A_PIXEL


async def test_a_file_picked_in_the_contents_of_a_story_lands_its_step_under_the_bar_from_its_reason_down(
    review_of_a_long_file_in_two_chapters: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(WIDE_SCREEN)
    await _read_as_story(page, review_of_a_long_file_in_two_chapters)

    # The long file as the second chapter lists it: its step there is the one with a reason
    await page.get_by_test_id("contents-file").nth(1).click()

    reason = page.get_by_test_id("step-reason")
    await expect(reason).to_be_in_viewport()
    assert abs(await _below_the_bar(page, reason)) < LESS_THAN_A_PIXEL


async def test_a_chapter_picked_in_the_contents_of_a_story_stands_at_the_top_of_what_is_read_under_no_bar(
    review_of_a_long_file_in_two_chapters: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(WIDE_SCREEN)
    await _read_as_story(page, review_of_a_long_file_in_two_chapters)
    the_second = page.get_by_test_id("story-chapter").nth(1)

    # The overview's entry, the first chapter's, then the second's
    await page.get_by_test_id("go-to-part").nth(2).click()

    await expect(page.get_by_test_id("go-to-part").nth(2)).to_have_attribute("aria-current", "location")
    below_the_top = await the_second.evaluate(TOP_OF) - await page.get_by_test_id("story-view").evaluate(TOP_OF)
    assert abs(below_the_top) < LESS_THAN_A_PIXEL
    await expect(page.get_by_test_id("chapter-bar")).to_have_count(0)


@pytest.mark.parametrize("line_key", LINE_KEYS)
async def test_a_line_key_after_a_chapter_picked_in_the_contents_lands_on_its_first_line_and_takes_the_reader_nowhere_back(
    review_of_a_long_file_in_two_chapters: RunningReview, page: Page, line_key: str
) -> None:
    """The pick leaves the keyboard on the contents' entry, outside what is read: the key starts where the reader reads."""
    await page.set_viewport_size(WIDE_SCREEN)
    await _read_as_story(page, review_of_a_long_file_in_two_chapters)
    story = page.get_by_test_id("story-view")
    the_second = page.get_by_test_id("story-chapter").nth(1)
    # The overview's entry, the first chapter's, then the second's
    await page.get_by_test_id("go-to-part").nth(2).click()
    await expect(page.get_by_test_id("go-to-part").nth(2)).to_have_attribute("aria-current", "location")
    scrolled_to = await story.evaluate(SCROLLED)

    await page.keyboard.press(line_key)

    await expect(the_second.get_by_role("button", name=FIRST_LINE_OF_THE_SECOND_CHAPTER, exact=True)).to_be_focused()
    assert await story.evaluate(SCROLLED) >= scrolled_to > 0


async def test_the_bar_of_a_chapter_takes_the_reader_to_the_head_of_the_next_and_the_keyboard_with_them(
    review_of_a_long_file_in_two_chapters: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review_of_a_long_file_in_two_chapters)
    story = page.get_by_test_id("story-view")
    the_second = page.get_by_test_id("story-chapter").nth(1)
    await story.evaluate("(area, depth) => area.scrollBy(0, depth)", DEEP_IN_THE_PIECE)

    await page.get_by_test_id("go-to-chapter-after").press("Enter")

    # At its head no bar is over it: the keyboard the bar's button held is on that head, and j goes on from there
    await expect(page.get_by_test_id("chapter-bar")).to_have_count(0)
    below_the_top = await the_second.evaluate(TOP_OF) - await story.evaluate(TOP_OF)
    assert abs(below_the_top) < LESS_THAN_A_PIXEL
    await expect(the_second.get_by_test_id("part-head")).to_be_focused()
    await page.keyboard.press("j")
    await expect(the_second.get_by_role("button", name=FIRST_LINE_OF_THE_SECOND_CHAPTER, exact=True)).to_be_focused()


async def test_the_head_of_a_chapter_holds_the_keyboard_the_bar_handed_it_only_until_the_keyboard_leaves(
    review_of_a_long_file_in_two_chapters: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review_of_a_long_file_in_two_chapters)
    the_second = page.get_by_test_id("story-chapter").nth(1)
    await page.get_by_test_id("story-view").evaluate("(area, depth) => area.scrollBy(0, depth)", DEEP_IN_THE_PIECE)
    await page.get_by_test_id("go-to-chapter-after").press("Enter")
    await expect(page.get_by_test_id("chapter-bar")).to_have_count(0)

    # The keyboard goes on to a line; a press on the head's words then is a press on any words
    await page.keyboard.press("j")
    await the_second.get_by_test_id("chapter-title").click()

    assert await page.evaluate(KEYBOARD_ON_NOTHING)


async def test_a_press_on_the_words_of_a_chapter_puts_the_keyboard_on_nothing(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review)

    await page.get_by_test_id("chapter-why").click()
    # A key, at which a browser rings whatever holds the keyboard
    await page.keyboard.press("Shift")

    assert await page.evaluate(KEYBOARD_ON_NOTHING)


async def test_f_puts_the_contents_of_a_story_away_and_their_rail_brings_them_back(
    review: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(WIDE_SCREEN)
    await _read_as_story(page, review)
    await expect(page.get_by_test_id("contents")).to_be_visible()

    await page.keyboard.press("f")
    await expect(page.get_by_test_id("contents")).to_have_count(0)

    await page.get_by_test_id("show-contents").click()
    await expect(page.get_by_test_id("contents")).to_be_visible()


async def test_the_keyboard_goes_with_the_contents_of_a_story_to_their_rail_and_comes_back_with_them(
    review: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(WIDE_SCREEN)
    await _read_as_story(page, review)

    await page.get_by_test_id("hide-contents").press("Enter")
    await expect(page.get_by_test_id("show-contents")).to_be_focused()

    await page.keyboard.press("Enter")
    await expect(page.get_by_test_id("hide-contents")).to_be_focused()


async def test_f_with_the_keyboard_on_an_entry_of_the_contents_of_a_story_leaves_it_on_their_rail(
    review: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(WIDE_SCREEN)
    await _read_as_story(page, review)
    await page.get_by_test_id("go-to-part").first.focus()

    await page.keyboard.press("f")

    await expect(page.get_by_test_id("show-contents")).to_be_focused()


async def test_the_contents_of_a_story_stand_as_wide_as_their_design_draws_them_and_widen_from_their_edge(
    review: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(WIDE_SCREEN)
    await _read_as_story(page, review)
    contents = page.get_by_test_id("contents")
    assert await contents.evaluate(WIDTH_OF) == CONTENTS_WIDTH_AT_FIRST

    # The edge the contents are sized by takes the keyboard: an arrow towards the story widens them a step
    await page.get_by_test_id("contents-resize").press("ArrowRight")

    assert await contents.evaluate(WIDTH_OF) > CONTENTS_WIDTH_AT_FIRST


async def test_on_a_narrow_screen_a_story_opens_without_its_contents_which_lie_over_it_once_brought_back(
    review: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(ZOOMED)
    await page.goto(review.url)
    await page.click('[data-testid="read-as-story"]')
    story = page.get_by_test_id("story-view")
    await page.wait_for_selector('[data-testid="story-piece"]')

    # Opened, nothing lies over the story: its contents are put away to their rail
    assert await page.get_by_test_id("contents").count() == 0
    rail = page.get_by_test_id("show-contents")
    assert await story.evaluate(LEFT_OF) >= await rail.evaluate(RIGHT_OF) - LESS_THAN_A_PIXEL

    # Brought back, they lie over the story, which keeps the screen's width under them
    await rail.click()
    assert await page.get_by_test_id("contents").evaluate(RIGHT_OF) > await story.evaluate(LEFT_OF)
    assert await story.evaluate(WIDTH_OF) >= await page.evaluate(WINDOW_WIDTH) - LESS_THAN_A_PIXEL


async def _read_the_first_chapter_through(page: Page, review: RunningReview) -> None:
    """Read a story with its contents beside it, from the head of its first chapter to where that chapter ends.

    The story opens with that head on screen, under an overview shorter than the screen; the chapter is
    longer than one, so its end comes on screen only once the reader has scrolled to it.
    """
    await page.set_viewport_size(WIDE_SCREEN)
    await _read_as_story(page, review)
    await expect(page.get_by_test_id("contents-count")).to_have_text(TWO_CHAPTERS)
    # The end of the overview comes first, then the first chapter's
    await page.get_by_test_id("part-end").nth(1).evaluate(TO_THE_MIDDLE)


async def test_a_chapter_scrolled_through_is_ticked_in_the_contents_and_its_files_step_back(
    review_of_a_long_file_in_two_chapters: RunningReview, page: Page
) -> None:
    await _read_the_first_chapter_through(page, review_of_a_long_file_in_two_chapters)

    await expect(page.get_by_test_id("contents-count")).to_have_text(ONE_OF_TWO_READ)
    # The overview's entry, then the first chapter's
    of_the_first = page.get_by_test_id("contents-entry").nth(1)
    await expect(of_the_first.get_by_test_id("part-read-mark")).to_be_visible()
    files_of_the_first, files_of_the_second = await page.get_by_test_id("contents-files").all()
    assert await files_of_the_first.evaluate(OPACITY_OF) < FULLY_DRAWN
    assert await files_of_the_second.evaluate(OPACITY_OF) == FULLY_DRAWN


async def test_what_was_read_of_a_story_is_still_read_once_the_page_is_loaded_again(
    review_of_a_long_file_in_two_chapters: RunningReview, page: Page
) -> None:
    await _read_the_first_chapter_through(page, review_of_a_long_file_in_two_chapters)
    await expect(page.get_by_test_id("contents-count")).to_have_text(ONE_OF_TWO_READ)

    await page.reload()

    await expect(page.get_by_test_id("contents-count")).to_have_text(ONE_OF_TWO_READ)


async def test_nothing_is_read_of_a_story_the_agent_has_told_again(
    review_of_a_long_file_in_two_chapters: RunningReview, page: Page
) -> None:
    await _read_the_first_chapter_through(page, review_of_a_long_file_in_two_chapters)
    await expect(page.get_by_test_id("contents-count")).to_have_text(ONE_OF_TWO_READ)

    async with AsyncClient(base_url=review_of_a_long_file_in_two_chapters.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(THE_LONG_FILE_IN_TWO_CHAPTERS))

    await expect(page.get_by_test_id("contents-count")).to_have_text(TWO_CHAPTERS)

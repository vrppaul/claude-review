"""E2E: a review read as the story the agent told of it, in a real browser.

A story is read down an area of its own: the bar of the chapter being read
stays at its top, and the header of the piece being read under it. Where a
step or a chapter gone to stands, where a line key lands, which parts the
contents mark as read, and how the story stands on a narrow screen are only
true in a browser.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Locator, Page, ViewportSize, expect

from claude_review.domain.models import LineSpan
from claude_review.domain.story import Step
from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.line_keys import LESS_THAN_A_LINE_APART, LINES_UNDER_THE_HEADER, SCROLLED
from tests.helpers import ReviewServers, RunningReview, committed_repository, repository_opening, write_files
from tests.stories import ONLY_CHAPTER, as_the_agent_writes, chapter_of, step, story_of, story_of_chapters

STORY_ROUTE = "/api/story"

TOLD_FILE = "told.py"
HOUSEKEEPING_FILE = "notes.txt"
COMMITTED_FILES = {TOLD_FILE: "keep one\nfirst two\nkeep three\n", HOUSEKEEPING_FILE: "a note\n"}
# The change under review: line 2 of the file the story tells, and a line of the file it names as housekeeping
THE_CHANGE = {TOLD_FILE: "keep one\nchanged two\nkeep three\n", HOUSEKEEPING_FILE: "another note\n"}
A_STORY = story_of(step(TOLD_FILE, 2, 2), housekeeping=(HOUSEKEEPING_FILE,))
# A file added whole, long enough that its piece runs far past the bottom of the screen
LONG_FILE = "long.py"
LINES_OF_THE_LONG_FILE = 200
# How far into the long piece the reader scrolls: well past its head, well short of its end
DEEP_IN_THE_PIECE = 1500
# The long file told in two steps, each longer than a screen: the last line the first of them tells,
# and why the second is as it is, said above its piece
LAST_LINE_OF_THE_FIRST_STEP = 100
REASON_OF_THE_SECOND_STEP = "The second half of the file goes on from the first."
# The frame a step's reason stands in, which is drawn from where the step begins: its words stand inside it
REASONS_FRAME = "step-reason-block-frame"
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
# How tall everything an area scrolls is, in pixels
HEIGHT_HELD = "(area) => area.scrollHeight"
# A wide screen zoomed in: too narrow for a column to stand beside what is read
ZOOMED: ViewportSize = {"width": 640, "height": 400}
PHONE: ViewportSize = {"width": 420, "height": 800}
# Where an element's left edge is, in pixels from the left of the window
LEFT_OF = "(element) => element.getBoundingClientRect().left"
# Where an element's top edge is on screen, in pixels from the top of the window
TOP_OF = "(element) => element.getBoundingClientRect().top"
# And its bottom edge
BOTTOM_OF = "(element) => element.getBoundingClientRect().bottom"
# Where an element's right edge is, in pixels from the left of the window
RIGHT_OF = "(element) => element.getBoundingClientRect().right"
# How wide an element is on screen, and how wide the window it is drawn in
WIDTH_OF = "(element) => element.getBoundingClientRect().width"
WINDOW_WIDTH = "window.innerWidth"
# Wide enough for the tree of files to stand beside them
WIDE_SCREEN: ViewportSize = {"width": 1600, "height": 900}
# What the head of the contents says of a story of two chapters: with neither scrolled past, and with one
TWO_CHAPTERS = "2 chapters"
ONE_OF_TWO_READ = "1 of 2 read"
# Bring an element to the top of the area it scrolls in, at once
TO_THE_TOP = "(element) => element.scrollIntoView({ block: 'start' })"
# Two frames drawn: what the browser watches on the page has reported where everything stood as it opened
TWO_FRAMES = "new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
# Whether nothing on the page holds the keyboard, and what does, by the test id it carries
KEYBOARD_ON_NOTHING = "document.activeElement === document.body"
HOLDS_THE_KEYBOARD = "document.activeElement?.dataset.testid"


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


async def test_a_line_key_deep_in_a_chapter_lands_on_the_first_line_in_sight_under_its_bar_and_the_header_of_its_piece(
    review_of_a_long_file: RunningReview, page: Page
) -> None:
    """Scrolled by hand, the keyboard is still on the switch in the header: the key starts at the first line the reader sees."""
    await _read_as_story(page, review_of_a_long_file)
    story = page.get_by_test_id("story-view")
    await story.evaluate("(area, depth) => area.scrollBy(0, depth)", DEEP_IN_THE_PIECE)
    await expect(page.get_by_test_id("chapter-bar")).to_be_in_viewport()

    await page.keyboard.press("j")

    # The story's one piece: its header is kept in sight under the bar, over its lines
    kept_in_sight = page.get_by_test_id("story-piece-header")
    assert await page.evaluate(HOLDS_THE_KEYBOARD) == "line-gutter"
    assert -LESS_THAN_A_LINE_APART <= await kept_in_sight.evaluate(LINES_UNDER_THE_HEADER) < 1
    assert await story.evaluate(SCROLLED) == DEEP_IN_THE_PIECE


async def test_a_step_gone_to_stands_right_under_the_bar_of_its_chapter_from_its_reason_down(
    review_of_a_long_file_in_two_steps: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review_of_a_long_file_in_two_steps)

    # Twice, so the reader ends on the second step wherever the first press took them from: ] goes no further than the last
    await page.keyboard.press("]")
    await page.keyboard.press("]")

    reason = page.get_by_test_id(REASONS_FRAME)
    await expect(reason).to_be_in_viewport()
    assert abs(await _below_the_bar(page, reason)) < LESS_THAN_A_PIXEL


async def test_a_file_picked_in_the_contents_of_a_story_lands_its_step_under_the_bar_from_its_reason_down(
    review_of_a_long_file_in_two_chapters: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(WIDE_SCREEN)
    await _read_as_story(page, review_of_a_long_file_in_two_chapters)

    # The long file as the second chapter lists it: its step there is the one with a reason
    await page.get_by_test_id("contents-file").nth(1).click()

    reason = page.get_by_test_id(REASONS_FRAME)
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


async def test_a_line_key_after_a_chapter_picked_in_the_contents_lands_on_its_first_line_and_takes_the_reader_nowhere_back(
    review_of_a_long_file_in_two_chapters: RunningReview, page: Page
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

    await page.keyboard.press("j")

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


async def test_on_a_phone_a_story_is_no_wider_than_the_screen(review: RunningReview, page: Page) -> None:
    await _read_as_story(page, review)

    await page.set_viewport_size(PHONE)

    assert await page.evaluate("document.documentElement.scrollWidth") == PHONE["width"]


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


async def _read_the_second_chapter(page: Page, review: RunningReview) -> None:
    """Read a story with its contents beside it, and scroll on until its second chapter is at the top.

    The story opens on an overview shorter than the screen; each chapter is longer than one.
    """
    await page.set_viewport_size(WIDE_SCREEN)
    await _read_as_story(page, review)
    await expect(page.get_by_test_id("contents-count")).to_have_text(TWO_CHAPTERS)
    await page.get_by_test_id("story-chapter").nth(1).evaluate(TO_THE_TOP)


async def test_the_overview_on_screen_as_the_story_opens_is_ticked_only_once_the_reader_scrolls_past_it(
    review_of_a_long_file_in_two_chapters: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(WIDE_SCREEN)
    await _read_as_story(page, review_of_a_long_file_in_two_chapters)
    of_the_overview = page.get_by_test_id("contents-entry").first
    await page.evaluate(TWO_FRAMES)
    await expect(of_the_overview.get_by_test_id("part-read-mark")).to_have_count(0)

    await page.get_by_test_id("story-chapter").first.evaluate(TO_THE_TOP)

    await expect(of_the_overview.get_by_test_id("part-read-mark")).to_be_visible()


async def test_a_chapter_above_the_one_being_read_is_ticked_in_the_contents(
    review_of_a_long_file_in_two_chapters: RunningReview, page: Page
) -> None:
    await _read_the_second_chapter(page, review_of_a_long_file_in_two_chapters)

    await expect(page.get_by_test_id("contents-count")).to_have_text(ONE_OF_TWO_READ)
    # The overview's entry, then the first chapter's
    of_the_first = page.get_by_test_id("contents-entry").nth(1)
    await expect(of_the_first.get_by_test_id("part-read-mark")).to_be_visible()


async def test_a_chapter_is_ticked_no_more_once_the_reader_scrolls_back_up_into_it(
    review_of_a_long_file_in_two_chapters: RunningReview, page: Page
) -> None:
    await _read_the_second_chapter(page, review_of_a_long_file_in_two_chapters)
    await expect(page.get_by_test_id("contents-count")).to_have_text(ONE_OF_TWO_READ)

    await page.get_by_test_id("story-chapter").first.evaluate(TO_THE_TOP)

    await expect(page.get_by_test_id("contents-count")).to_have_text(TWO_CHAPTERS)

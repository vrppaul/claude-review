"""E2E: a review read as the story the agent told of it, in a real browser.

A story is read down an area of its own. That a step or a chapter gone to
comes into view, where a line key lands, and which parts the contents mark
as read are only true in a browser.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Page, ViewportSize, expect

from claude_review.domain.models import LineSpan
from claude_review.domain.story import Step
from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.page_reads import FOCUSED_ELEMENT, FOCUSED_TEST_ID, SCROLLED
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
# A step's reason, the top line of the frame its step stands in, where the step begins
REASONS_LINE = "step-reason-block"
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
# Wide enough for the tree of files to stand beside them
WIDE_SCREEN: ViewportSize = {"width": 1600, "height": 900}
# What the head of the contents says of a story of two chapters: with neither scrolled past, and with one
TWO_CHAPTERS = "2 chapters"
ONE_OF_TWO_READ = "1 of 2 read"
# Bring an element to the top of the area it scrolls in, at once
TO_THE_TOP = "(element) => element.scrollIntoView({ block: 'start' })"
# Two frames drawn: what the browser watches on the page has reported where everything stood as it opened
TWO_FRAMES = "new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
# Whether nothing on the page holds the keyboard
KEYBOARD_ON_NOTHING = "document.activeElement === document.body"


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


async def test_a_line_key_deep_in_a_chapter_lands_on_a_line_the_reader_sees_and_leaves_the_story_where_it_is(
    review_of_a_long_file: RunningReview, page: Page
) -> None:
    """Scrolled by hand, the keyboard is still on the switch in the header: the key starts where the reader reads.

    The pointer is brought to the line it lands on: one under the chapter's bar or its piece's header would be
    scrolled out to reach.
    """
    await _read_as_story(page, review_of_a_long_file)
    story = page.get_by_test_id("story-view")
    await story.evaluate("(area, depth) => area.scrollBy(0, depth)", DEEP_IN_THE_PIECE)
    await expect(page.get_by_test_id("chapter-bar")).to_be_in_viewport()

    await page.keyboard.press("j")
    await page.locator(FOCUSED_ELEMENT).hover()

    assert await page.evaluate(FOCUSED_TEST_ID) == "line-gutter"
    assert await story.evaluate(SCROLLED) == DEEP_IN_THE_PIECE


async def test_a_step_gone_to_brings_its_reason_into_view(
    review_of_a_long_file_in_two_steps: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review_of_a_long_file_in_two_steps)

    # Twice, so the reader ends on the second step wherever the first press took them from: ] goes no further than the last
    await page.keyboard.press("]")
    await page.keyboard.press("]")

    await expect(page.get_by_test_id(REASONS_LINE)).to_be_in_viewport()


async def test_a_file_picked_in_the_contents_of_a_story_brings_the_reason_of_its_step_into_view(
    review_of_a_long_file_in_two_chapters: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(WIDE_SCREEN)
    await _read_as_story(page, review_of_a_long_file_in_two_chapters)

    # The long file as the second chapter lists it: its step there is the one with a reason
    await page.get_by_test_id("contents-file").nth(1).click()

    await expect(page.get_by_test_id(REASONS_LINE)).to_be_in_viewport()


async def test_a_chapter_picked_in_the_contents_of_a_story_comes_into_view_under_no_bar(
    review_of_a_long_file_in_two_chapters: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(WIDE_SCREEN)
    await _read_as_story(page, review_of_a_long_file_in_two_chapters)
    the_second = page.get_by_test_id("story-chapter").nth(1)

    # The overview's entry, the first chapter's, then the second's
    await page.get_by_test_id("go-to-part").nth(2).click()

    await expect(page.get_by_test_id("go-to-part").nth(2)).to_have_attribute("aria-current", "location")
    await expect(the_second.get_by_test_id("part-head")).to_be_in_viewport()
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

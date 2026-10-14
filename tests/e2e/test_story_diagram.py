"""E2E: a story's diagram, drawn by mermaid in a real browser.

Whether a source draws only a browser can say: mermaid lays a drawing out
by measuring its labels on the page. It draws under the policy the page is
served with, loaded only once a story has a diagram, and a press on a node
the agent linked to a chapter takes the reader there. A source it cannot
read is said to be broken where it breaks.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Page, ViewportSize, expect

from claude_review.domain.story import Step, Story
from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.helpers import ReviewServers, RunningReview, committed_repository, repository_opening, write_files
from tests.stories import ONLY_CHAPTER, as_the_agent_writes, chapter_of, planted, step, story_of_chapters

STORY_ROUTE = "/api/story"
# What Chromium writes on the console about anything the page's policy refused
REFUSED_BY_THE_POLICY = "Content Security Policy"

# The change: a file added whole, long enough that its second half is far down the story
COMMITTED_FILES = {"notes.txt": "a note\n"}
LONG_FILE = "long.py"
LINES_OF_THE_LONG_FILE = 200
LAST_LINE_OF_THE_FIRST_HALF = 100
SECOND_CHAPTER = "ch-2"
# The overview draws the two halves, a chapter each, after a node that leads nowhere
CAPTION = "How the file is told"
DRAWN = "flowchart LR\n  asked[Asked for] --> first[The first half] --> second[The second half]"
# The same with its third line's arrow drawn twice, where mermaid's parser stops
BROKEN = "flowchart LR\n  asked[Asked for] --> first[The first half]\n  first --> --> second[The second half]"
# The nodes the page marks as leading somewhere, in the order mermaid draws them: the first half, the second
LEADING_SOMEWHERE = "[data-role='diagram-link']"
THE_SECOND_HALF = 1
# Wide enough for the contents to stand beside the story
WIDE_SCREEN: ViewportSize = {"width": 1600, "height": 900}


def _told_in_two_chapters(drawn: str) -> Story[Step]:
    """The long file told in two chapters, its overview drawing them as written here."""
    story = story_of_chapters(
        chapter_of(ONLY_CHAPTER, step(LONG_FILE, 1, LAST_LINE_OF_THE_FIRST_HALF)),
        chapter_of(SECOND_CHAPTER, step(LONG_FILE, LAST_LINE_OF_THE_FIRST_HALF + 1, LINES_OF_THE_LONG_FILE)),
    )
    diagram = {"mermaid": drawn, "caption": CAPTION, "links": {"first": ONLY_CHAPTER, "second": SECOND_CHAPTER}}
    return planted(story, ("overview", "diagram"), diagram)


@pytest.fixture
def long_file_repo(tmp_path: Path) -> Path:
    """A repository whose change adds one file whole, longer than any screen."""
    repo = committed_repository(tmp_path / "long", COMMITTED_FILES)
    write_files(repo, {LONG_FILE: "".join(f"line {number}\n" for number in range(1, LINES_OF_THE_LONG_FILE + 1))})
    return repo


async def _told(repo: Path, servers: ReviewServers, story: Story[Step]) -> RunningReview:
    started = await servers.start(await repository_opening(repo))
    async with AsyncClient(base_url=started.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(story))
    return started


@in_the_browsers_loop
async def review_drawn(long_file_repo: Path, servers: ReviewServers) -> RunningReview:
    """A review whose story's overview draws its two chapters."""
    return await _told(long_file_repo, servers, _told_in_two_chapters(DRAWN))


@in_the_browsers_loop
async def review_drawn_broken(long_file_repo: Path, servers: ReviewServers) -> RunningReview:
    """A review whose story's overview draws them with a source mermaid cannot read."""
    return await _told(long_file_repo, servers, _told_in_two_chapters(BROKEN))


async def _read_as_story(page: Page, review: RunningReview) -> None:
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    await page.click('[data-testid="read-as-story"]')
    await page.wait_for_selector('[data-testid="story-piece"]')


async def test_a_diagram_is_drawn_under_the_pages_policy_and_nothing_is_refused(
    review_drawn: RunningReview, page: Page
) -> None:
    console: list[str] = []
    page.on("console", lambda message: console.append(message.text))

    await _read_as_story(page, review_drawn)

    await expect(page.get_by_test_id("diagram-drawing").locator("svg")).to_have_count(1)
    assert [said for said in console if REFUSED_BY_THE_POLICY in said] == []


async def test_a_press_on_a_node_takes_the_reader_to_the_chapter_it_leads_to(
    review_drawn: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(WIDE_SCREEN)
    await _read_as_story(page, review_drawn)

    await page.get_by_test_id("diagram-drawing").locator(LEADING_SOMEWHERE).nth(THE_SECOND_HALF).click()

    # The overview's entry of the contents, the first chapter's, then the second's
    await expect(page.get_by_test_id("go-to-part").nth(2)).to_have_attribute("aria-current", "location")


async def test_a_diagram_that_does_not_draw_says_where_it_breaks_and_shows_its_source(
    review_drawn_broken: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review_drawn_broken)

    await expect(page.get_by_test_id("diagram-fault")).to_have_text(
        'This diagram could not be drawn: line 3, unexpected "-->".'
    )
    await expect(page.get_by_test_id("diagram-source")).to_have_text(BROKEN)

"""E2E: every row of the page is the library's Row, drawn one way wherever it stands, in a real browser.

A row is one item of a list the reader goes down: a file or a folder of the
tree, a part of a story in its contents and what hangs under it, a fold, an
entry of Help, an option of a pane, a thread the screen on it cannot draw.
Every row of one line stands as tall as the others, and a title longer than
its row is wide wraps onto more lines, whole. Every one is lit under the
pointer by the pointer's light, stands on the selected tint with its edge
at its start while it is the one of its list the reader is at, and steps
back into faint words once they have finished with it. How tall a row
stands and how it is lit are the stylesheet's, worked out by the browser:
jsdom applies none. Each look is read against its token, painted on a
probe in the same theme.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Locator, Page, expect

from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.painted import light, on_a_probe, painted
from tests.helpers import (
    EVENTS_ROUTE,
    FIRST_THREAD_ID,
    GLANCE_AT_EVENTS,
    ReviewServers,
    RunningReview,
    committed_repository,
    repository_opening,
    write_files,
)
from tests.stories import as_the_agent_writes, planted, step, story_of

# The themes the reader's system may ask for, which a review follows until the reader picks one
SCHEMES = ["light", "dark"]
# How tall every row stands, in pixels
ROW_HEIGHT = 32
# What a row shows while nothing is laid over its ground
NOTHING_LAID = "none"

# A file in a folder, which the story leaves out; a file the agent calls housekeeping; and a file added whole,
# longer than a screen, which the story tells in one chapter and which the work answering round 1 changes
LEFT_OUT_FILE = "src/left_out.py"
HOUSEKEEPING_FILE = "notes.txt"
TOLD_FILE = "told.py"
TOLD_LINES = 80
COMMITTED = {LEFT_OUT_FILE: "left as it was\n", HOUSEKEEPING_FILE: "a note\n"}
BEFORE_ROUND_ONE = {
    LEFT_OUT_FILE: "left as it is now\n",
    HOUSEKEEPING_FILE: "another note\n",
    TOLD_FILE: "".join(f"line {number}\n" for number in range(1, TOLD_LINES + 1)),
}
ANSWERING_ROUND_ONE = {TOLD_FILE: "".join(f"line {number}\n" for number in range(1, TOLD_LINES + 2))}
# The story of the change: the told file in one chapter, the notes as housekeeping, and a decision its overview
# lists, which a row folds away under the overview
A_DECISION = {"text": "Told in one chapter, as it is one change.", "chapter": None}
A_STORY = planted(
    story_of(step(TOLD_FILE, 1, TOLD_LINES + 1), housekeeping=(HOUSEKEEPING_FILE,)),
    ("overview", "decisions"),
    [A_DECISION],
)
STORY_ROUTE = "/api/story"
RETAKE_ROUTE = "/api/retake"
# Where the agent answers a thread
REPLY_ROUTE = "/api/reply"

# The rows of the tree: its one folder, and its three files
FOLDER = "folder-item"
FILE = "file-item"
THE_TREE = {FOLDER: 1, FILE: 3}
# The rows of Help, of the base picker and of the finish pane, once a comment is written: the tour; this review,
# round 1 and the branch the repository stands on; the comment
IN_HELP = {"take-tour": 1}
IN_THE_BASE_PICKER = {"base-option": 3}
IN_THE_FINISH_PANE = {"finish-comment": 1}
# The rows of the picker of what a message points at, once a comment is written, and of the replies, once the
# agent answers it: the thread and the files; the thread answered
IN_THE_PICKER = {"thread-option": 1, "file-option": 3}
IN_THE_REPLIES = {"reply-row": 1}
# The rows of the threads a narrower base cannot draw: the one comment, on a file round 1 did not change
OFF_SCREEN = {"off-screen-thread": 1}
# The rows of a story's contents and of its overview, housekeeping unfolded where both list it: the overview's
# entry and the chapter's, the told file under the chapter and the left-out file under what the story leaves out,
# what it leaves out, housekeeping and its file, and what more the overview lists
IN_THE_STORY = {
    "go-to-part": 2,
    "contents-file": 2,
    "contents-left-out": 1,
    "fold-housekeeping": 2,
    "housekeeping-file": 2,
    "story-more-toggle": 1,
}
# Bring an element to the top of the area it scrolls in, at once
TO_THE_TOP = "(element) => element.scrollIntoView({ block: 'start' })"
# The row of the file the reader is in, which says so to whoever cannot see it, and every other; there is one
SAID_CURRENT_BY = "aria-current"
CURRENT = "true"
SAID_CURRENT = f'[{SAID_CURRENT_BY}="{CURRENT}"]'
NOT_IN_VIEW = f":not({SAID_CURRENT})"
THE_FILE_IN_VIEW = 1
# What the check of the base in force says to whoever cannot see it; and the base of round 1, as the picker names it
IN_FORCE = "In force"
ROUND_ONE = "round 1"


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A repository with a change in it, some of it done after round 1 began."""
    committed_repository(tmp_path, COMMITTED)
    write_files(tmp_path, BEFORE_ROUND_ONE)
    return tmp_path


@in_the_browsers_loop
async def review(repository: Path, servers: ReviewServers) -> RunningReview:
    """A review that has been through round 1, whose agent has told the story of the change as it stands."""
    started = await servers.start(await repository_opening(repository))
    async with AsyncClient(base_url=started.url) as agent:
        await agent.post(RETAKE_ROUTE, json={})
        write_files(repository, ANSWERING_ROUND_ONE)
        await agent.post(RETAKE_ROUTE, json={})
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(A_STORY))
    return started


async def _open_in(page: Page, review: RunningReview, scheme: str) -> None:
    """Open the review for a reader whose system asks for a theme."""
    await page.emulate_media(color_scheme=scheme)
    await page.goto(review.url)
    await page.get_by_test_id("sidebar").wait_for()


async def _comment_on_the_first_line(page: Page) -> None:
    """Put a comment on the review's first line from the keyboard: a line of the left-out file, in its folder."""
    await page.keyboard.press("j")
    await page.keyboard.press("Enter")
    await page.get_by_test_id("comment-input").wait_for()
    await page.keyboard.type("Name it after the unit")
    await page.keyboard.press("Control+Enter")
    await page.get_by_test_id("thread-card").wait_for()


async def _send_the_round(page: Page) -> None:
    """Send what is written with the round, which hands its threads to the agent."""
    await page.get_by_test_id("quick-submit").click()
    await page.get_by_test_id("modal-submit").click()
    await page.get_by_test_id("finish-review").wait_for(state="detached")


async def _rows(page: Page, counted: dict[str, int]) -> list[Locator]:
    """Every row of these test ids, once the page draws as many of each as are counted."""
    for test_id, count in counted.items():
        await page.get_by_test_id(test_id).nth(count - 1).wait_for()
    return [row for test_id in counted for row in await page.get_by_test_id(test_id).all()]


async def _rows_not_in_view(page: Page, counted: dict[str, int]) -> list[Locator]:
    """Every row of these test ids but the one that says it stands for the file the reader is in."""
    return [
        row for test_id in counted for row in await page.get_by_test_id(test_id).and_(page.locator(NOT_IN_VIEW)).all()
    ]


async def _counted(page: Page, counted: dict[str, int]) -> dict[str, int]:
    """How many rows of each test id the page draws."""
    return {test_id: await page.get_by_test_id(test_id).count() for test_id in counted}


async def _heights(rows: list[Locator]) -> list[float]:
    return [(await painted(row)).height for row in rows]


async def _lit_under_the_pointer(rows: list[Locator]) -> list[str]:
    """What is laid over each row's ground while the pointer is on it."""
    lit = []
    for row in rows:
        await row.hover()
        lit.append((await painted(row)).laid)
    return lit


async def _expect_rows_of_one_height_lit_by_the_pointer(page: Page, counted: dict[str, int]) -> None:
    """Every row of these test ids is found, stands one row tall, and is lit by the pointer's light under it."""
    rows = await _rows(page, counted)

    assert await _counted(page, counted) == counted
    assert await _heights(rows) == [ROW_HEIGHT] * len(rows)
    assert await _lit_under_the_pointer(rows) == [await light(page, "--cr-hover")] * len(rows)


async def _expect_drawn_as_current(page: Page, row: Locator) -> None:
    """The row the reader is at: on the selected tint, its edge at its start, and the pointer leaves it so."""
    await row.hover()
    current = await painted(row)

    assert (current.ground, current.edge, current.laid, current.height) == (
        await on_a_probe(page, "backgroundColor", "var(--cr-selected)"),
        await on_a_probe(page, "boxShadow", "var(--cr-shadow-selected-start)"),
        NOTHING_LAID,
        ROW_HEIGHT,
    )


async def _expect_stepped_back(page: Page, row: Locator) -> None:
    """A row the reader has finished with: its words faint."""
    assert (await painted(row)).words == await on_a_probe(page, "color", "var(--cr-faint)")


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_the_rows_of_the_tree_stand_one_height_and_are_lit_by_the_pointer_the_file_in_view_selected_and_a_viewed_one_faint(
    review: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review, scheme)
    await page.locator(f'[data-testid="file-section"][data-path="{TOLD_FILE}"]').get_by_test_id("viewed-toggle").check()
    in_view = page.get_by_test_id(FILE).and_(page.locator(SAID_CURRENT))
    viewed = page.get_by_test_id(FILE).filter(has_text=TOLD_FILE)

    await _expect_drawn_as_current(page, in_view)
    await _expect_stepped_back(page, viewed)
    rows = await _rows(page, THE_TREE)
    assert await _counted(page, THE_TREE) == THE_TREE
    assert await _heights(rows) == [ROW_HEIGHT] * len(rows)
    lit = await _lit_under_the_pointer(await _rows_not_in_view(page, THE_TREE))
    assert lit == [await light(page, "--cr-hover")] * (len(rows) - THE_FILE_IN_VIEW)


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_the_rows_of_help_of_the_base_picker_and_of_the_finish_pane_stand_one_height_and_are_lit_by_the_pointer(
    review: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review, scheme)
    await _comment_on_the_first_line(page)

    await page.get_by_test_id("open-help").click()
    await _expect_rows_of_one_height_lit_by_the_pointer(page, IN_HELP)
    await page.keyboard.press("Escape")
    await page.get_by_test_id("quick-submit").click()
    await _expect_rows_of_one_height_lit_by_the_pointer(page, IN_THE_FINISH_PANE)
    await page.keyboard.press("Escape")
    await page.get_by_test_id("base-picker").click()
    rows = await _rows(page, IN_THE_BASE_PICKER)
    in_force = page.get_by_test_id("base-option").filter(has=page.get_by_label(IN_FORCE))
    not_in_force = page.get_by_test_id("base-option").filter(has_not=page.get_by_label(IN_FORCE))

    await _expect_drawn_as_current(page, in_force)
    assert await _counted(page, IN_THE_BASE_PICKER) == IN_THE_BASE_PICKER
    assert await _heights(rows) == [ROW_HEIGHT] * len(rows)
    others = await not_in_force.all()
    assert await _lit_under_the_pointer(others) == [await light(page, "--cr-hover")] * len(others)


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_the_rows_of_the_picker_of_what_a_message_points_at_and_of_the_replies_stand_one_height_lit_by_the_pointer_or_the_keys(
    review: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review, scheme)
    await _comment_on_the_first_line(page)
    async with AsyncClient(base_url=review.url) as agent:
        await agent.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)
        await _send_the_round(page)
        await agent.post(REPLY_ROUTE, json={"thread_id": FIRST_THREAD_ID, "body": "It is named after the unit now."})
    await page.get_by_test_id("unread-count").wait_for()

    await page.get_by_test_id("panel-input").fill("Look again at @")
    lit_by_the_keys = page.get_by_test_id("thread-option")
    await _expect_drawn_as_current(page, lit_by_the_keys)
    rows = await _rows(page, IN_THE_PICKER)
    assert await _counted(page, IN_THE_PICKER) == IN_THE_PICKER
    assert await _heights(rows) == [ROW_HEIGHT] * len(rows)
    files = await page.get_by_test_id("file-option").all()
    assert await _lit_under_the_pointer(files) == [await light(page, "--cr-hover")] * len(files)
    await page.get_by_test_id("panel-input").fill("")
    await page.get_by_test_id("replies-menu").click()
    await _expect_rows_of_one_height_lit_by_the_pointer(page, IN_THE_REPLIES)


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_the_rows_of_the_threads_a_narrower_base_cannot_draw_stand_one_height_and_are_lit_by_the_pointer(
    review: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review, scheme)
    await _comment_on_the_first_line(page)
    await page.get_by_test_id("base-picker").click()
    await page.get_by_test_id("base-option").filter(has_text=ROUND_ONE).click()

    await page.get_by_test_id("list-off-screen").click()

    await _expect_rows_of_one_height_lit_by_the_pointer(page, OFF_SCREEN)


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_the_rows_of_a_story_stand_as_the_trees_do_and_a_part_scrolled_past_steps_back_while_the_file_read_is_selected(
    review: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review, scheme)
    await page.get_by_test_id("read-as-story").click()
    for fold in await page.get_by_test_id("fold-housekeeping").all():
        await fold.click()
    await page.get_by_test_id("story-chapter").get_by_test_id("story-piece").evaluate(TO_THE_TOP)
    told = page.get_by_test_id("contents-file").filter(has_text=TOLD_FILE)
    await expect(told).to_have_attribute(SAID_CURRENT_BY, CURRENT)
    rows = await _rows(page, IN_THE_STORY)

    await _expect_stepped_back(page, page.get_by_test_id("go-to-part").first)
    await _expect_drawn_as_current(page, told)
    assert await _counted(page, IN_THE_STORY) == IN_THE_STORY
    assert await _heights(rows) == [ROW_HEIGHT] * len(rows)
    lit = await _lit_under_the_pointer(await _rows_not_in_view(page, IN_THE_STORY))
    assert lit == [await light(page, "--cr-hover")] * (len(rows) - THE_FILE_IN_VIEW)


# A chapter's title longer than a story's contents are wide, as long as a chapter's title may be
LONG_TITLE = "Every greeting is shorter, and so are the tests reading them"
A_STORY_OF_A_LONG_TITLE = planted(A_STORY, ("chapters", 0, "title"), LONG_TITLE)
# What of an element is cut where it ends: each element in it whose words reach past its edge
CUT = """(element) => [...element.querySelectorAll('*')].filter(
    (inside) => inside.scrollWidth > inside.clientWidth
).length"""
# Where an element's middle stands down the window, and where its top does, in pixels
MIDDLE = "(element) => { const box = element.getBoundingClientRect(); return box.top + box.height / 2; }"
TOP = "(element) => element.getBoundingClientRect().top"


@in_the_browsers_loop
async def review_of_a_long_title(repository: Path, servers: ReviewServers) -> RunningReview:
    """A review of the change as round 1's work leaves it, whose story names its chapter by a long title."""
    write_files(repository, ANSWERING_ROUND_ONE)
    started = await servers.start(await repository_opening(repository))
    async with AsyncClient(base_url=started.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(A_STORY_OF_A_LONG_TITLE))
    return started


async def test_a_chapter_whose_title_is_longer_than_the_contents_are_wide_wraps_onto_more_lines_and_reads_whole(
    review_of_a_long_title: RunningReview, page: Page
) -> None:
    await page.goto(review_of_a_long_title.url)
    await page.get_by_test_id("read-as-story").click()

    chapter = page.get_by_test_id("go-to-part").filter(has_text=LONG_TITLE)

    assert (await painted(chapter)).height > ROW_HEIGHT
    assert await chapter.evaluate(CUT) == 0
    # Its node stands level with its first line, as in a row of one line, so the axis through the nodes meets it
    node_middle = await chapter.get_by_test_id("part-node").evaluate(MIDDLE)
    assert node_middle - await chapter.evaluate(TOP) == ROW_HEIGHT / 2

"""E2E: the parts of the page's component library, painted by their tokens, in a real browser.

How a part looks at rest, under the pointer, pressed, open and while it
cannot be pressed is the stylesheet's, worked out by the browser: jsdom
applies no stylesheet. Each look is read against the token it is painted
with, drawn on a probe in the same theme, so a part painted with a token of
another meaning fails here in either theme.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Locator, Page
from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import CommentSeverity
from claude_review.hosting.workspace import ReaderFiles
from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.painted import light, on_a_probe, painted
from tests.helpers import (
    EVENTS_ROUTE,
    GLANCE_AT_EVENTS,
    ReviewServers,
    RunningReview,
    committed_repository,
    line_on_the_wire,
    repository_opening,
    write_files,
)
from tests.stories import as_the_agent_writes, planted, step, story_of

# One file, changed on a line, so the first line number the keys reach is in it
CHANGED_FILE = "main.py"
COMMITTED = {CHANGED_FILE: "def hello():\n    return 'hello'\n"}
CHANGED = {CHANGED_FILE: "def hello():\n    return 'hi'\n"}
# The themes the reader's system may ask for, which a review follows until the reader picks one
SCHEMES = ["light", "dark"]
# Where the pointer rests when it is on none of the parts read: the top left corner, over the header's words
AWAY = (0, 0)
# How tall a button stands among words and small controls, and where it ends a pane, a card or a bar, in pixels
XS = 24
SM = 32
# What a part shows while nothing is laid over its ground, and the weight of words that are not set in bold
NOTHING_LAID = "none"
REGULAR = "400"
BOLD = "600"
# Whether a button can be pressed: set from here, as no one view of the page holds a part of every tone disabled
DISABLED = "(button, disabled) => { button.disabled = disabled; }"


class Tone(BaseModel):
    """A part of one tone the page draws, and the tokens it is painted with at rest, pointed at and disabled.

    Each is a CSS value naming a token, or the value the tone sets where it names none.
    """

    model_config = ConfigDict(frozen=True)

    said: str
    test_id: str
    ground: str
    words: str
    light: str
    ground_disabled: str
    height: float


# Every tone the page shows beside a thread, once one is written and whitespace is hidden: each tone, at both
# sizes between them
BESIDE_A_THREAD = [
    Tone(
        said="primary",
        test_id="quick-submit",
        ground="var(--cr-control)",
        words="var(--color-primary-content)",
        light="--cr-hover-on-fill",
        ground_disabled="var(--color-base-300)",
        height=SM,
    ),
    Tone(
        said="quiet, an icon alone",
        test_id="prev-comment",
        ground="transparent",
        words="var(--color-base-content)",
        light="--cr-hover",
        ground_disabled="transparent",
        height=XS,
    ),
    Tone(
        said="secondary",
        test_id="resolve-comment",
        ground="var(--color-base-100)",
        words="var(--color-base-content)",
        light="--cr-hover",
        ground_disabled="var(--color-base-100)",
        height=XS,
    ),
    Tone(
        said="marked",
        test_id="whitespace-hidden",
        ground="var(--cr-mark-tint)",
        words="var(--cr-mark-text)",
        light="--cr-hover",
        ground_disabled="var(--cr-mark-tint)",
        height=XS,
    ),
]
# And in the question asked before a thread is deleted, which holds the page's keyboard while it is open
IN_THE_DELETE_QUESTION = [
    Tone(
        said="quiet",
        test_id="confirm-keep",
        ground="transparent",
        words="var(--color-base-content)",
        light="--cr-hover",
        ground_disabled="transparent",
        height=SM,
    ),
    Tone(
        said="danger",
        test_id="confirm-go-ahead",
        ground="var(--color-error)",
        words="var(--color-error-content)",
        light="--cr-hover-on-fill",
        ground_disabled="var(--color-base-300)",
        height=SM,
    ),
]
# A button that is an icon alone, at each size, as a review opens: the tree's, put away, and the settings
ICONS_ALONE = [("hide-sidebar", XS), ("settings-toggle", SM)]
# Where the agent says something in the panel, and what it is doing while it does it
SAY_ROUTE = "/api/say"
PROGRESS_ROUTE = "/api/progress"
# How far what an element holds stands in from its edge, above and at its start, and how wide that edge is
ROOM = """(element) => {
    const style = getComputedStyle(element);
    return [style.paddingTop, style.paddingLeft, style.borderTopWidth];
}"""
# The edge round a card: a line
A_LINE = "1px"
# The shadow a card casts: lifted off what it hangs under, or lying where it is drawn
HANGING = "var(--cr-shadow-hanging)"
LYING = "none"


class Card(BaseModel):
    """A card the page draws, by its test id, and the shadow it casts there."""

    model_config = ConfigDict(frozen=True)

    test_id: str
    lift: str


class CardLook(BaseModel):
    """How a card is drawn: its ground and corner, the room round what it holds and the edge round that, its shadow."""

    model_config = ConfigDict(frozen=True)

    ground: str
    corner: str
    room: tuple[str, str, str]
    lift: str


# Every card the page draws, each where a review shows it: a comment being written and the thread it becomes, under
# their line; the agent's answer in the panel and its work while it does it; the facts of a story on its way
BEING_WRITTEN = Card(test_id="comment-box", lift=HANGING)
A_THREAD = Card(test_id="thread-card", lift=HANGING)
AN_ANSWER = Card(test_id="panel-answer", lift=LYING)
AT_WORK = Card(test_id="panel-work", lift=LYING)
ON_ITS_WAY = Card(test_id="story-wait-facts", lift=LYING)
EVERY_CARD = [BEING_WRITTEN, A_THREAD, AN_ANSWER, AT_WORK, ON_ITS_WAY]

# Where the agent tells the story of the change
STORY_ROUTE = "/api/story"
# A story of the change whose overview draws it in a source mermaid cannot read, which the story shows instead
NOT_DRAWN = "flowchart LR\n  asked[Asked for] --> --> told[Told]"
A_STORY_NOT_DRAWN = planted(
    story_of(step(CHANGED_FILE, 2, 2)), ("overview", "diagram"), {"mermaid": NOT_DRAWN, "caption": None, "links": {}}
)
# Code set apart to read or copy as written: the commands to attach an agent by hand, folded in the panel while
# none is attached; and the source of a story's diagram that did not draw
ATTACH_COMMANDS = "attach-commands"
DIAGRAM_SOURCE = "diagram-source"
EVERY_CODE_BOX = [ATTACH_COMMANDS, DIAGRAM_SOURCE]
# Open a fold from here: what opens it is its summary, which carries no test id of its own
UNFOLDED = "(fold) => { fold.open = true; }"


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A repository with one file changed and not committed."""
    committed_repository(tmp_path, COMMITTED)
    write_files(tmp_path, CHANGED)
    return tmp_path


@in_the_browsers_loop
async def review(repository: Path, servers: ReviewServers) -> RunningReview:
    return await servers.start(await repository_opening(repository))


async def _open_in(page: Page, review: RunningReview, scheme: str) -> None:
    """Open the review for a reader whose system asks for a theme."""
    await page.emulate_media(color_scheme=scheme)
    await page.goto(review.url)
    await page.get_by_test_id("sidebar").wait_for()


async def _hide_whitespace(page: Page) -> None:
    """Hide changes of whitespace from the settings, which the header says from then on."""
    await page.get_by_test_id("settings-toggle").click()
    await page.get_by_test_id("ignore-whitespace").check()
    await page.keyboard.press("Escape")
    await page.get_by_test_id("whitespace-hidden").wait_for()


async def _comment_on_the_first_line(page: Page) -> None:
    """Put a comment on the review's first line from the keyboard, so its thread and what goes with it are drawn."""
    await page.keyboard.press("j")
    await page.keyboard.press("Enter")
    await page.get_by_test_id("comment-input").wait_for()
    await page.keyboard.type("Name it after the unit")
    await page.keyboard.press("Control+Enter")
    await page.get_by_test_id("thread-card").wait_for()


async def _an_agent_attaches_and_answers(review: RunningReview) -> None:
    """An agent looks for what the reader handed over, says something in the panel, and says what it is doing."""
    async with AsyncClient(base_url=review.url) as agent:
        await agent.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)
        await agent.post(SAY_ROUTE, json={"body": "The greeting is shorter now."})
        await agent.post(PROGRESS_ROUTE, json={"text": "Reading the tests of the greeting"})


async def _the_agent_tells_a_story_not_drawn(review: RunningReview) -> None:
    """The agent tells a story of the change whose diagram does not draw: from then on it is attached."""
    async with AsyncClient(base_url=review.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(A_STORY_NOT_DRAWN))


async def _wait_for_a_story(page: Page) -> None:
    """Turn stories on behind the gear, and read the review as its story while the agent writes it."""
    await page.get_by_test_id("settings-toggle").click()
    await page.get_by_test_id("stories").check()
    await page.keyboard.press("Escape")
    await page.get_by_test_id("read-as-story").click()
    await page.get_by_test_id(ON_ITS_WAY.test_id).wait_for()


async def _look_of(page: Page, card: Card) -> CardLook:
    """How a card is drawn, as the browser works it out."""
    drawn = page.get_by_test_id(card.test_id)
    look = await painted(drawn)
    return CardLook(ground=look.ground, corner=look.radius, room=tuple(await drawn.evaluate(ROOM)), lift=look.edge)


async def _expect_painted_by_its_tokens(page: Page, tone: Tone) -> None:
    """A part of a tone, at rest, under the pointer, and while it cannot be pressed, against its tokens."""
    part = page.get_by_test_id(tone.test_id)
    ground = await on_a_probe(page, "backgroundColor", tone.ground)
    await page.mouse.move(*AWAY)

    at_rest = await painted(part)
    await part.hover()
    pointed_at = await painted(part)
    await part.evaluate(DISABLED, True)
    disabled_pointed_at = await painted(part)
    await page.mouse.move(*AWAY)
    disabled = await painted(part)
    await part.evaluate(DISABLED, False)

    assert (at_rest.ground, at_rest.words, at_rest.laid, at_rest.height) == (
        ground,
        await on_a_probe(page, "color", tone.words),
        NOTHING_LAID,
        tone.height,
    ), tone.said
    assert (pointed_at.ground, pointed_at.laid) == (ground, await light(page, tone.light)), tone.said
    assert (disabled.ground, disabled.words) == (
        await on_a_probe(page, "backgroundColor", tone.ground_disabled),
        await on_a_probe(page, "color", "var(--cr-muted)"),
    ), tone.said
    assert disabled_pointed_at.laid == NOTHING_LAID, tone.said


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_a_button_of_every_tone_is_painted_by_its_tokens_at_rest_under_the_pointer_and_while_it_cannot_be_pressed(
    review: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review, scheme)
    await _hide_whitespace(page)
    await _comment_on_the_first_line(page)

    for tone in BESIDE_A_THREAD:
        await _expect_painted_by_its_tokens(page, tone)
    await page.get_by_test_id("delete-comment").click()
    for tone in IN_THE_DELETE_QUESTION:
        await _expect_painted_by_its_tokens(page, tone)


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_a_filled_button_whose_pane_is_open_keeps_its_fill_and_its_words_with_an_edge_at_its_foot_in_their_colour(
    review: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review, scheme)
    trigger = page.get_by_test_id("quick-submit")
    closed = await painted(trigger)

    await trigger.click()
    await page.mouse.move(*AWAY)

    opened = await painted(trigger)
    edge = await on_a_probe(page, "boxShadow", "var(--cr-shadow-selected-foot-on-fill)", opened.words)
    assert (opened.ground, opened.words, opened.edge) == (closed.ground, closed.words, edge)


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_a_segment_pressed_stands_on_the_selected_tint_with_its_edge_at_its_foot_in_bold_and_the_pointer_leaves_it_so(
    review: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review, scheme)
    await page.get_by_test_id("settings-toggle").click()
    pressed = page.get_by_test_id("layout-unified")

    await pressed.hover()

    segment = await painted(pressed)
    not_pressed = await painted(page.get_by_test_id("layout-split"))
    assert (segment.ground, segment.laid, segment.edge, segment.words, segment.weight) == (
        await on_a_probe(page, "backgroundColor", "transparent"),
        await light(page, "--cr-selected"),
        await on_a_probe(page, "boxShadow", "var(--cr-shadow-selected-foot)"),
        await on_a_probe(page, "color", "var(--color-base-content)"),
        BOLD,
    )
    assert (not_pressed.laid, not_pressed.edge, not_pressed.weight) == (NOTHING_LAID, NOTHING_LAID, REGULAR)


@pytest.mark.parametrize(("test_id", "height"), ICONS_ALONE)
async def test_a_button_that_is_an_icon_alone_is_as_wide_as_it_is_tall(
    review: RunningReview, page: Page, test_id: str, height: float
) -> None:
    await _open_in(page, review, SCHEMES[0])

    box = await page.get_by_test_id(test_id).bounding_box()

    assert box is not None
    assert (box["width"], box["height"]) == (height, height)


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_a_columns_grip_under_the_pointer_shows_the_edge_of_the_one_the_reader_is_at(
    review: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review, scheme)
    grip = page.get_by_test_id("sidebar-resize")

    await grip.hover()

    assert (await painted(grip)).ground == await on_a_probe(page, "backgroundColor", "var(--cr-selected-edge)")


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_every_card_stands_on_one_ground_corner_and_room_inside_a_line_lifted_only_where_it_hangs_under_a_line(
    review: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review, scheme)
    await page.keyboard.press("j")
    await page.keyboard.press("Enter")
    being_written = await _look_of(page, BEING_WRITTEN)
    await page.keyboard.type("Name it after the unit")
    await page.keyboard.press("Control+Enter")
    await page.get_by_test_id(A_THREAD.test_id).wait_for()
    await _an_agent_attaches_and_answers(review)
    await page.get_by_test_id(AT_WORK.test_id).wait_for()
    in_the_files = [being_written, *[await _look_of(page, card) for card in [A_THREAD, AN_ANSWER, AT_WORK]]]

    await _wait_for_a_story(page)

    looks = [*in_the_files, await _look_of(page, ON_ITS_WAY)]
    ground = await on_a_probe(page, "backgroundColor", "var(--color-base-200)")
    corner = await on_a_probe(page, "borderTopLeftRadius", "var(--radius-box)")
    room = (
        await on_a_probe(page, "paddingTop", "var(--cr-card-room-block)"),
        await on_a_probe(page, "paddingLeft", "var(--cr-card-room-inline)"),
        A_LINE,
    )
    every_card = len(EVERY_CARD)
    assert [look.ground for look in looks] == [ground] * every_card
    assert [look.corner for look in looks] == [corner] * every_card
    assert [look.room for look in looks] == [room] * every_card
    assert [look.lift for look in looks] == [await on_a_probe(page, "boxShadow", card.lift) for card in EVERY_CARD]


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_code_set_apart_is_one_box_in_the_codes_face_and_size_on_a_cards_ground_edge_and_corner(
    review: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review, scheme)
    await page.get_by_test_id("toggle-panel").click()
    await page.get_by_test_id("panel-attach-by-hand").evaluate(UNFOLDED)
    commands = page.get_by_test_id(ATTACH_COMMANDS)
    looks = [await painted(commands)]
    rooms = [tuple(await commands.evaluate(ROOM))]
    await _the_agent_tells_a_story_not_drawn(review)
    # Opened from the note that says it is ready: Story pressed before the story reaches the page asks first
    await page.get_by_test_id("open-story").click()
    source = page.get_by_test_id(DIAGRAM_SOURCE)
    looks.append(await painted(source))
    rooms.append(tuple(await source.evaluate(ROOM)))

    words = (
        await on_a_probe(page, "fontSize", "var(--cr-code-size)"),
        await on_a_probe(page, "fontFamily", "var(--font-mono)"),
    )
    box = (
        await on_a_probe(page, "backgroundColor", "var(--color-base-200)"),
        await on_a_probe(page, "borderTopColor", "var(--color-base-300)"),
        await on_a_probe(page, "borderTopLeftRadius", "var(--radius-box)"),
    )
    every_box = len(EVERY_CODE_BOX)
    assert [(look.size, look.face) for look in looks] == [words] * every_box
    assert [(look.ground, look.border, look.radius) for look in looks] == [box] * every_box
    assert rooms == [rooms[0]] * every_box


# A script made runnable, its lines the same: a change of its mode alone, which its file's notes say
RUNNABLE_SCRIPT = "run.sh"
RUNNABLE = 0o755
WITH_A_SCRIPT = {**COMMITTED, RUNNABLE_SCRIPT: "#!/bin/sh\necho hello\n"}
# Where the agent takes the diff again, as it does after a round; and a file written after that, which moves the
# tree on under the diff
RETAKE_ROUTE = "/api/retake"
MOVED_ON = {"later.py": "LATER = True\n"}
# How far a notice's words stand in from its edge, above them and at its start
NOTICE_ROOM = """(element) => {
    const style = getComputedStyle(element);
    return [style.paddingTop, style.paddingLeft];
}"""


class Notice(BaseModel):
    """A notice the page draws, by its test id, and the tokens of its tone: the ground under it and its words."""

    model_config = ConfigDict(frozen=True)

    test_id: str
    ground: str
    words: str


class NoticeLook(BaseModel):
    """How a notice is drawn: how tall it stands, the room round its words, their size, its ground and their colour."""

    model_config = ConfigDict(frozen=True)

    height: float
    room: tuple[str, str]
    size: str
    ground: str
    words: str


# A notice of each tone, in the order a review shows them: the code moving on under the reader, a warning; a fact
# of a file its lines cannot show, quiet; the comments the reader had not sent, brought back, their own doing; and
# the review sent, done
MOVED = Notice(test_id="tree-moved", ground="var(--cr-warning-tint)", words="var(--color-base-content)")
MODE_CHANGED = Notice(test_id="mode-change-note", ground="var(--color-base-200)", words="var(--cr-muted)")
RESTORED = Notice(test_id="restored-notice", ground="var(--cr-mark-soft)", words="var(--color-base-content)")
SENT = Notice(test_id="submitted-banner", ground="var(--color-base-200)", words="var(--color-base-content)")
EVERY_NOTICE = [MOVED, MODE_CHANGED, RESTORED, SENT]
# The colour of the mark each notice that is news stands by, in the same order; a fact of a file is no news
MARKS = ["var(--color-warning)", "var(--cr-mark)", "var(--cr-done)"]


@pytest.fixture
def repository_with_a_script(tmp_path: Path) -> Path:
    """A repository with one file changed and a script made runnable, neither committed."""
    committed_repository(tmp_path, WITH_A_SCRIPT)
    write_files(tmp_path, CHANGED)
    (tmp_path / RUNNABLE_SCRIPT).chmod(RUNNABLE)
    return tmp_path


@in_the_browsers_loop
async def review_moved_on(repository_with_a_script: Path, servers: ReviewServers) -> RunningReview:
    """A review whose diff the agent took again, after which the tree moved on under it."""
    review = await servers.start(await repository_opening(repository_with_a_script))
    async with AsyncClient(base_url=review.url) as agent:
        await agent.post(RETAKE_ROUTE, json={})
    write_files(repository_with_a_script, MOVED_ON)
    return review


def _pixels(value: str) -> float:
    """A length as the browser works it out, in pixels."""
    return float(value.removesuffix("px"))


async def _look_of_a_notice(page: Page, notice: Notice) -> NoticeLook:
    """How a notice is drawn, once it is, as the browser works it out."""
    drawn = page.get_by_test_id(notice.test_id)
    await drawn.wait_for()
    look = await painted(drawn)
    room_block, room_inline = await drawn.evaluate(NOTICE_ROOM)
    return NoticeLook(
        height=look.height, room=(room_block, room_inline), size=look.size, ground=look.ground, words=look.words
    )


async def _mark_of(page: Page, notice: Notice) -> str:
    """The colour of the mark a notice stands by."""
    return (await painted(page.get_by_test_id(f"{notice.test_id}-mark"))).words


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_every_notice_is_as_tall_as_one_with_a_button_its_words_alike_on_its_tones_ground_marked_in_its_colour(
    review_moved_on: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review_moved_on, scheme)
    looks = [await _look_of_a_notice(page, notice) for notice in [MOVED, MODE_CHANGED]]
    marks = [await _mark_of(page, MOVED)]
    await _comment_on_the_first_line(page)
    await page.reload()
    looks.append(await _look_of_a_notice(page, RESTORED))
    marks.append(await _mark_of(page, RESTORED))

    await page.get_by_test_id("quick-submit").click()
    await page.get_by_test_id("modal-submit").click()

    looks.append(await _look_of_a_notice(page, SENT))
    marks.append(await _mark_of(page, SENT))
    room_block = await on_a_probe(page, "paddingTop", "var(--cr-notice-room-block)")
    room_inline = await on_a_probe(page, "paddingLeft", "var(--cr-notice-room-inline)")
    words = await on_a_probe(page, "fontSize", "var(--text-xs)")
    every_notice = len(EVERY_NOTICE)
    assert [look.height for look in looks] == [XS + 2 * _pixels(room_block) + _pixels(A_LINE)] * every_notice
    assert [(look.room, look.size) for look in looks] == [((room_block, room_inline), words)] * every_notice
    assert [(look.ground, look.words) for look in looks] == [
        (await on_a_probe(page, "backgroundColor", notice.ground), await on_a_probe(page, "color", notice.words))
        for notice in EVERY_NOTICE
    ]
    assert marks == [await on_a_probe(page, "color", colour) for colour in MARKS]


# Where the agent raises a thread on a line, and the line of the changed file it raises them on
POINT_ROUTE = "/api/point"
CHANGED_LINE = 2
# Every tag, count and chip a review draws once the agent raised a question on a line, each where it stands: what
# the thread asks for and that it is the agent's, on its card; how many threads hang on the file, on its header and
# on its row of the tree; what handing the review over costs, and the thread named in the panel's note of it; and
# what the thread asks for, in the list a round is sent from
EVERY_MARK_IN_A_LINE = [
    "comment-severity",
    "comment-raised",
    "section-comment-count",
    "file-threads",
    "review-weight",
    "panel-thread-ref",
    "finish-severity",
]


class MarkBox(BaseModel):
    """How a mark standing in a line is boxed: how tall, at what corner, in words of what size."""

    model_config = ConfigDict(frozen=True)

    height: float
    corner: str
    size: str


async def _the_agent_raises_a_question(review: RunningReview) -> None:
    """The agent raises a question on the changed line."""
    raised = {
        "anchor": line_on_the_wire(CHANGED_FILE, CHANGED_LINE),
        "body": "Is the short greeting on purpose?",
        "severity": CommentSeverity.QUESTION,
    }
    async with AsyncClient(base_url=review.url) as agent:
        (await agent.post(POINT_ROUTE, json=raised)).raise_for_status()


async def _box_of(page: Page, test_id: str) -> MarkBox:
    """How the first mark of a test id is boxed, as the browser works it out."""
    look = await painted(page.get_by_test_id(test_id).first)
    return MarkBox(height=look.height, corner=look.radius, size=look.size)


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_every_tag_count_and_chip_stands_in_one_box_at_a_fields_corner_whatever_line_it_stands_in(
    review: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review, scheme)
    await page.get_by_test_id("toggle-panel").click()
    await _the_agent_raises_a_question(review)
    await page.get_by_test_id("comment-severity").wait_for()
    await page.get_by_test_id("quick-submit").click()
    await page.get_by_test_id("finish-severity").wait_for()

    boxes = [await _box_of(page, test_id) for test_id in EVERY_MARK_IN_A_LINE]

    corner = await on_a_probe(page, "borderTopLeftRadius", "var(--radius-field)")
    assert boxes == [MarkBox(height=boxes[0].height, corner=corner, size=boxes[0].size)] * len(EVERY_MARK_IN_A_LINE)


# Every dot a review draws once an agent is at work and raised a thread, each where it stands: how the agent stands
# with the review, in the header; that the thread's answer is new, on its card; and the dots that breathe while the
# agent works, on the card of its work
EVERY_DOT = ["presence-dot", "comment-unread-dot", "breathing-dot"]
# A dot is round: each corner half its size
ROUND = "50%"
# Every key of the keyboard the help shows: its own, on the button that opens it, and those it lists
EVERY_KEY = ["help-key", "shortcut-key"]


class DotLook(BaseModel):
    """How a dot is drawn: how wide and how tall, and how round."""

    model_config = ConfigDict(frozen=True)

    width: float
    height: float
    corner: str


class KeyLook(BaseModel):
    """How a key is drawn: how tall, at what corner, in words of what size, weight and face."""

    model_config = ConfigDict(frozen=True)

    height: float
    corner: str
    size: str
    weight: str
    face: str


async def _dot_of(page: Page, test_id: str) -> DotLook:
    """How the first dot of a test id is drawn, as the browser works it out."""
    dot = page.get_by_test_id(test_id).first
    look = await painted(dot)
    box = await dot.bounding_box()
    assert box is not None
    return DotLook(width=box["width"], height=look.height, corner=look.radius)


async def _key_of(page: Page, test_id: str) -> KeyLook:
    """How the first key of a test id is drawn, as the browser works it out."""
    look = await painted(page.get_by_test_id(test_id).first)
    return KeyLook(height=look.height, corner=look.radius, size=look.size, weight=look.weight, face=look.face)


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_every_dot_is_drawn_at_one_size_and_round(review: RunningReview, page: Page, scheme: str) -> None:
    await _open_in(page, review, scheme)
    await page.get_by_test_id("toggle-panel").click()
    await _an_agent_attaches_and_answers(review)
    await _the_agent_raises_a_question(review)
    await page.get_by_test_id("comment-unread-dot").wait_for()
    await page.get_by_test_id("breathing-dot").first.wait_for()

    dots = [await _dot_of(page, test_id) for test_id in EVERY_DOT]

    assert dots == [DotLook(width=dots[0].height, height=dots[0].height, corner=ROUND)] * len(EVERY_DOT)


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_every_key_the_help_shows_stands_in_one_box_in_the_codes_regular_face(
    review: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review, scheme)
    await page.get_by_test_id("open-help").click()
    await page.get_by_test_id("shortcut-key").first.wait_for()

    keys = [await _key_of(page, test_id) for test_id in EVERY_KEY]

    face = await on_a_probe(page, "fontFamily", "var(--font-mono)")
    corner = await on_a_probe(page, "borderTopLeftRadius", "var(--radius-field)")
    one_box = KeyLook(height=keys[0].height, corner=corner, size=keys[0].size, weight=REGULAR, face=face)
    assert keys == [one_box] * len(EVERY_KEY)


# Every turn of the panel once the agent answered, said what it is doing, and the reader asked it something: its
# answer, its work on what was asked, and what the reader asked
EVERY_TURN = ["panel-answer", "panel-working", "panel-said"]
# How far a turn's words stand in from its outer edge, above them and at their start, its edge included, and how
# round its corners are
TURN_INSET = """(turn) => {
    const style = getComputedStyle(turn);
    return [
        parseFloat(style.borderTopWidth) + parseFloat(style.paddingTop),
        parseFloat(style.borderLeftWidth) + parseFloat(style.paddingLeft),
        style.borderTopLeftRadius,
        style.borderTopRightRadius,
    ];
}"""


async def test_every_turn_of_the_panel_stands_its_words_as_far_in_from_its_edge_at_one_corner(
    review: RunningReview, page: Page
) -> None:
    await page.goto(review.url)
    await page.get_by_test_id("toggle-panel").click()
    await _an_agent_attaches_and_answers(review)
    await page.get_by_test_id("panel-input").fill("Why is it shorter?")
    await page.get_by_test_id("send-message").click()
    await page.get_by_test_id("panel-said").wait_for()

    insets = [await page.get_by_test_id(test_id).evaluate(TURN_INSET) for test_id in EVERY_TURN]

    assert insets == [insets[0]] * len(EVERY_TURN)


async def _heading_size(heading: Locator) -> tuple[str, str]:
    """The size and weight of a heading's words, as the browser works them out."""
    look = await painted(heading)
    return (look.size, look.weight)


async def test_the_guides_welcome_and_its_tour_are_headed_at_the_size_of_every_panes_heading(
    review: RunningReview, reader_files: ReaderFiles, page: Page
) -> None:
    reader_files.guide.unlink()
    await page.goto(review.url)
    sizes = [await _heading_size(page.get_by_test_id("guide-welcome-heading"))]

    await page.get_by_test_id("guide-start").click()

    sizes.append(await _heading_size(page.get_by_test_id("guide-tour").get_by_role("heading")))
    pane_heading = (await on_a_probe(page, "fontSize", "var(--text-sm)"), BOLD)
    assert sizes == [pane_heading, pane_heading]

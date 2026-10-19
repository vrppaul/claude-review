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
from playwright.async_api import Page
from pydantic import BaseModel, ConfigDict

from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.painted import light, on_a_probe, painted
from tests.helpers import (
    EVENTS_ROUTE,
    GLANCE_AT_EVENTS,
    ReviewServers,
    RunningReview,
    committed_repository,
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

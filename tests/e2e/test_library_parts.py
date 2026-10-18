"""E2E: the parts of the page's component library, painted by their tokens, in a real browser.

How a part looks at rest, under the pointer, pressed, open and while it
cannot be pressed is the stylesheet's, worked out by the browser: jsdom
applies no stylesheet. Each look is read against the token it is painted
with, drawn on a probe in the same theme, so a part painted with a token of
another meaning fails here in either theme.
"""

from pathlib import Path

import pytest
from playwright.async_api import Locator, Page
from pydantic import BaseModel, ConfigDict

from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.helpers import ReviewServers, RunningReview, committed_repository, repository_opening, write_files

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

# How an element is painted, as the browser works it out: its ground, what is laid over it, its words, the edge
# drawn inside it, the weight of its words and how tall it stands
PAINTED = """(element) => {
    const style = getComputedStyle(element);
    return {
        ground: style.backgroundColor,
        laid: style.backgroundImage,
        words: style.color,
        edge: style.boxShadow,
        weight: style.fontWeight,
        height: element.getBoundingClientRect().height,
    };
}"""
# A value painted on a probe, as the browser works it out in the theme the page is in: a property of the probe's
# style, what it is set to, and the colour of the probe's words, which a value naming the words' colour takes
ON_A_PROBE = """([property, value, words]) => {
    const probe = document.createElement('span');
    probe.style.color = words;
    probe.style[property] = value;
    document.body.append(probe);
    const painted = getComputedStyle(probe)[property];
    probe.remove();
    return painted;
}"""
# Whether a button can be pressed: set from here, as no one view of the page holds a part of every tone disabled
DISABLED = "(button, disabled) => { button.disabled = disabled; }"


class Painted(BaseModel):
    """How an element is painted, as PAINTED reads it."""

    model_config = ConfigDict(frozen=True)

    ground: str
    laid: str
    words: str
    edge: str
    weight: str
    height: float


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


# Every tone the page shows beside a thread, once one is written: each tone, at both sizes between them
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
    """Open the review for a reader whose system asks for a theme, the page put away from nothing."""
    await page.emulate_media(color_scheme=scheme)
    await page.goto(review.url)
    await page.get_by_test_id("sidebar").wait_for()


async def _comment_on_the_first_line(page: Page) -> None:
    """Put a comment on the review's first line from the keyboard, so its thread and what goes with it are drawn."""
    await page.keyboard.press("j")
    await page.keyboard.press("Enter")
    await page.get_by_test_id("comment-input").wait_for()
    await page.keyboard.type("Name it after the unit")
    await page.keyboard.press("Control+Enter")
    await page.get_by_test_id("thread-card").wait_for()


async def _painted(part: Locator) -> Painted:
    return Painted.model_validate(await part.evaluate(PAINTED))


async def _on_a_probe(page: Page, property_name: str, value: str, words: str = "inherit") -> str:
    return await page.evaluate(ON_A_PROBE, [property_name, value, words])


async def _light(page: Page, token: str) -> str:
    """The pointer's light a token is, laid over a ground as the stylesheet lays it."""
    return await _on_a_probe(page, "backgroundImage", f"linear-gradient(var({token}), var({token}))")


async def _expect_painted_by_its_tokens(page: Page, tone: Tone) -> None:
    """A part of a tone, at rest, under the pointer, and while it cannot be pressed, against its tokens."""
    part = page.get_by_test_id(tone.test_id)
    ground = await _on_a_probe(page, "backgroundColor", tone.ground)
    await page.mouse.move(*AWAY)

    at_rest = await _painted(part)
    await part.hover()
    pointed_at = await _painted(part)
    await part.evaluate(DISABLED, True)
    disabled_pointed_at = await _painted(part)
    await page.mouse.move(*AWAY)
    disabled = await _painted(part)
    await part.evaluate(DISABLED, False)

    assert (at_rest.ground, at_rest.words, at_rest.laid, at_rest.height) == (
        ground,
        await _on_a_probe(page, "color", tone.words),
        NOTHING_LAID,
        tone.height,
    ), tone.said
    assert (pointed_at.ground, pointed_at.laid) == (ground, await _light(page, tone.light)), tone.said
    assert (disabled.ground, disabled.words) == (
        await _on_a_probe(page, "backgroundColor", tone.ground_disabled),
        await _on_a_probe(page, "color", "var(--cr-muted)"),
    ), tone.said
    assert disabled_pointed_at.laid == NOTHING_LAID, tone.said


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_a_button_of_every_tone_is_painted_by_its_tokens_at_rest_under_the_pointer_and_while_it_cannot_be_pressed(
    review: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review, scheme)
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
    closed = await _painted(trigger)

    await trigger.click()
    await page.mouse.move(*AWAY)

    opened = await _painted(trigger)
    edge = await _on_a_probe(page, "boxShadow", "var(--cr-shadow-selected-foot-on-fill)", opened.words)
    assert (opened.ground, opened.words, opened.edge) == (closed.ground, closed.words, edge)


@pytest.mark.parametrize("scheme", SCHEMES)
async def test_a_segment_pressed_stands_on_the_selected_tint_with_its_edge_at_its_foot_in_bold_and_the_pointer_leaves_it_so(
    review: RunningReview, page: Page, scheme: str
) -> None:
    await _open_in(page, review, scheme)
    await page.get_by_test_id("settings-toggle").click()
    pressed = page.get_by_test_id("layout-unified")

    await pressed.hover()

    painted = await _painted(pressed)
    not_pressed = await _painted(page.get_by_test_id("layout-split"))
    assert (painted.ground, painted.laid, painted.edge, painted.words, painted.weight) == (
        await _on_a_probe(page, "backgroundColor", "transparent"),
        await _light(page, "--cr-selected"),
        await _on_a_probe(page, "boxShadow", "var(--cr-shadow-selected-foot)"),
        await _on_a_probe(page, "color", "var(--color-base-content)"),
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

    assert (await _painted(grip)).ground == await _on_a_probe(page, "backgroundColor", "var(--cr-selected-edge)")

"""What the browser tests read of how an element is painted, and of a token painted on a probe.

jsdom applies no stylesheet: an element's ground, its words' colour, its
edge and its face are the browser's to work out. A token is followed to what
it is in the theme the page is in by painting it on a probe, read as the
browser works it out, so it compares with an element's own.
"""

from playwright.async_api import Locator, Page
from pydantic import BaseModel, ConfigDict

# How an element is painted, as the browser works it out: its ground, what is laid over it, its words, the edge
# drawn inside it or the shadow it casts, the colour of its border and how round its corners are, the size,
# weight and face of its words, and how tall it stands
_PAINTED = """(element) => {
    const style = getComputedStyle(element);
    return {
        ground: style.backgroundColor,
        laid: style.backgroundImage,
        words: style.color,
        edge: style.boxShadow,
        border: style.borderTopColor,
        radius: style.borderTopLeftRadius,
        size: style.fontSize,
        weight: style.fontWeight,
        face: style.fontFamily,
        height: element.getBoundingClientRect().height,
    };
}"""
# A value painted on a probe: a property of the probe's style, what it is set to, and the colour of the probe's
# words, which a value naming the words' colour takes
_ON_A_PROBE = """([property, value, words]) => {
    const probe = document.createElement('span');
    probe.style.color = words;
    probe.style[property] = value;
    document.body.append(probe);
    const painted = getComputedStyle(probe)[property];
    probe.remove();
    return painted;
}"""
# The colour a probe's words take when nothing names one: the page's own
_THE_PAGES_WORDS = "inherit"


class Painted(BaseModel):
    """How an element is painted, as the browser works it out."""

    model_config = ConfigDict(frozen=True)

    ground: str
    laid: str
    words: str
    edge: str
    border: str
    radius: str
    size: str
    weight: str
    face: str
    height: float


async def painted(element: Locator) -> Painted:
    """How an element is painted."""
    return Painted.model_validate(await element.evaluate(_PAINTED))


async def on_a_probe(page: Page, property_name: str, value: str, words: str = _THE_PAGES_WORDS) -> str:
    """A value of a property, as the browser works it out on a probe: a token it names, in the page's theme."""
    return await page.evaluate(_ON_A_PROBE, [property_name, value, words])


async def light(page: Page, token: str) -> str:
    """The light a token is, laid over a ground as the stylesheet lays the pointer's and the selected tint."""
    return await on_a_probe(page, "backgroundImage", f"linear-gradient(var({token}), var({token}))")

"""What the browser tests read of the page — how far it and its areas have scrolled, what holds the keyboard — and
the scroll and the frames they wait for as a reader reads."""

# How far down an area has scrolled, in pixels
SCROLLED = "(area) => area.scrollTop"
# How far the page itself has scrolled: never, as only its areas and panes scroll
PAGE_SCROLLED_BY = "() => window.scrollY"
# Which element holds the keyboard, by its test id
FOCUSED_TEST_ID = "document.activeElement?.dataset.testid"
# Whatever holds the keyboard, as a locator finds it
FOCUSED_ELEMENT = ":focus"
# An element brought to the top of the area it scrolls in, as a reader reading from it
BROUGHT_TO_THE_TOP = "(element) => element.scrollIntoView({ block: 'start' })"
# Let the page draw a number of frames
FRAMES_DRAWN = (
    "async (count) => { for (let frame = 0; frame < count; frame += 1) await new Promise(requestAnimationFrame); }"
)

"""What the browser tests read of the page: how far it and its areas have scrolled, and what holds the keyboard."""

# How far down an area has scrolled, in pixels
SCROLLED = "(area) => area.scrollTop"
# How far the page itself has scrolled: never, as only its areas and panes scroll
PAGE_SCROLLED_BY = "() => window.scrollY"
# Which element holds the keyboard, by its test id
FOCUSED_TEST_ID = "document.activeElement?.dataset.testid"
# Whatever holds the keyboard, as a locator finds it
FOCUSED_ELEMENT = ":focus"

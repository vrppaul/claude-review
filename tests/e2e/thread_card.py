"""What the browser tests of a thread's card ask of the page, under a line of a file and under the story's words alike."""

# Whether the tail of a card is drawn: what the browser draws before the card's own contents; and how far in from
# the card's left edge it stands
TAIL_DRAWN = "(card) => getComputedStyle(card, '::before').content !== 'none'"
TAIL_AT = "(card) => getComputedStyle(card, '::before').left"
# Where the left, top and right edges of an element are on screen, in pixels
EDGES = "(element) => { const box = element.getBoundingClientRect(); return [box.left, box.top, box.right]; }"
# How far a card stands in from each side of what it hangs under, and the most it stands under it, as the boards
# draw them: under a line of a file and under a block of the story's words alike
CARD_INSET = 12
MOST_UNDER_ITS_LINE = 12

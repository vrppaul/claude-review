"""What the browser tests of a thread's card ask of the page, under a line of a file and under the story's words alike."""

# Whether the tail of a card is drawn: what the browser draws before the card's own contents
TAIL_DRAWN = "(card) => getComputedStyle(card, '::before').content !== 'none'"

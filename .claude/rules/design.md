---
paths:
  - "frontend/**"
---

# How the page looks

From the owner's design canvas of 2026-10-20. How the page answers the reader: `.claude/rules/design-behaviour.md`; how a design is made: `.claude/rules/design-process.md`.
How a part is built and where a value lives: `.claude/rules/page.md`.
A part is held to these once it is moved to them, or once a change touches its look.

## Colour

- A hue says whose a thing is or what it means, nothing else: blue the reader (their marks, their acts, the keyboard); purple the agent.
- Green and red are the change (added and removed, done and failed); yellow what to look at (a doubt, a blocker, out of date); red also danger (what cannot be undone, a failure).
- Words — plain, muted, faint — and the pointer's light are ink.
- No state is a hue: what is chosen, current or under the pointer is drawn in ink. Only the keyboard is blue, and only as its ring or an edge.
- Every hue climbs one ladder in both themes: solid, its words, border 35%, chip 18%, tint 12%, wash 6%. No other strength is used.
- Every step comes from its hue's one base value, so a theme sets one value per hue.
- A chip's ground is its hue mixed with the reading ground, not laid over what is under it, so a chip is one colour wherever it stands.
- A tag is its hue's chip under its hue's words, with no edge.
- Contrast is measured, never judged by eye: words 4.5:1 against their ground in every state; a state the reader needs, and the focus ring, 3:1; the pointer's light 1.15:1.
- White words go only on a fill dark enough for them: the dark theme fills a button with a darker blue than its marks.
- A weight is one the library names, each for its use: normal for what is read, semibold for what heads it, medium for a small label.

## Surfaces

- What is read is the lighter surface in both themes: in the light theme the reading area is white and the side columns grey; in the dark theme the reading area is the lighter of the two.
- A card stands one step off the ground under it: on the reading area, it takes the side columns' ground.
- Every part wears the page's current look: one left in a look the page has dropped is redrawn.
- One thing has one look wherever it stands: a file's code in a story's step as in Files; a way to a chapter in a list as on a file's bar.
- Two kinds of one thing are one element, of one room, type and height.
- A thing not there yet is drawn as what it will become, on a dashed edge: a comment being written is the card it becomes.

## Sizes and room

- Controls side by side are one height; so is every control in the header.
- Every head on the row under the header — a side column's bar, a put-away column's rail, a file's bar — is one height.
- A card's parts — its bar, its body, its foot — keep one room either side, so all three start and end on one edge.
- A thread hangs the full width of what it is under, with the page's own inset.
- Items of a list stand apart, a hairline or a gap between them, never touching.
- Things of one group stand closer together than the groups do.
- A light round words — the pointer's, the reader's place — reaches `--spacing(1.5)` past them above and below and `--spacing(2)` either side, and stands at least that far from anything else.
- The rows of a list stand on the edges of the field that filters it.
- Keys listed against their words stand in two columns, the keys right-aligned and the words left-aligned, close together.
- Chips and tags on a heading's line are centred on it.
- Only a title follows its number; what comes under it starts on the section's own edge.
- What matters most is drawn most plainly, never in faint words; what explains a part reads quieter than what explains the whole.

## States

- Every pressable thing is drawn at rest, under the pointer, chosen or current, with the keyboard on it, and off; one that can be new has that state too.
- What is chosen is marked the more weakly the larger it is: a small thing reversed, a row a pill.
- A small thing chosen — a segment, a pressed toggle, a button whose pane is open — is reversed: an ink ground, its words in the ground's colour.
- The row or band the reader is at is a grey pill of ink at 12%, rounded, with no edge, its words in ink.
- A field or a card the keyboard is in turns its edge blue, twice as strong, with nothing outside it; anything else the keyboard is on shows the ring.
- Off is faint words.
- A thing that is new carries a dot in the colour of who brought it.
- What only says has no states and looks like no control: no edge, a tint, words of normal weight.
- What acts looks like it acts: a way on is a button, never coloured words alone.

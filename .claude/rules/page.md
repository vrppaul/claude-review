---
paths:
  - "frontend/**"
---

# The page

How a part of the page is built is said at the top of its module. What eslint and stylelint refuse, and why, is said in `frontend/eslint.config.js` and `frontend/stylelint.config.js`.

## Types and state

- Svelte 5 runes; TypeScript in strict mode, no `any`.
- The compiler takes a value read from a list or a table by position or key as possibly missing. Build so that holds, never check around it: a line carries its markup rather than sitting beside it in another list.
- A place the reader is at is the thing they are at (an id), not its position in a list that changes.
- Find, walk or pair things; reach for an index only where the position is the meaning.
- A function an interface asks for is written as a property (`label: (anchor: Kind) => string`), so the compiler holds it to its parameter types.
- A component's module script exports nothing another module imports: eslint reads a `.svelte` import only through Svelte's catch-all declaration. A type or a function others use lives in a `.ts` module.
- A callback handed to a child component or to `<svelte:window>` names its parameter's type; svelte-check holds it to the prop.
- An object or array only ever replaced whole — what the server sent, a list rebuilt with `map`, `filter` or a spread — is `$state.raw`, never deep `$state`, which wraps every line of a diff in a proxy and pays for it on every read.

## Parts and elements

- The parts of `frontend/src/lib/` build on each other in one direction, as `LAYERS` in `frontend/eslint.config.js` lists them: components build on everything, and only components build on them.
- The page's own code never finds an element by test id or by a page-wide id. An element announces itself to whoever needs it, as every file section and thread does to `FileSections`.
- A selector that cannot be avoided reads a `data-role`, or one of two attributes that say which of many an element stands for: `data-place`, the line a line number is, and `data-tour`, the name the tour lights a place by.
- Every new button, input, textarea and container gets a `data-testid`, for the tests to act on.
- A change to what the reader sees is looked at in a browser before it is called done: light, dark and a narrow screen, and the page itself must not have scrolled. `scripts/look.py` is that look.

## Styling

- A colour, a layer or a shadow is written once, in `frontend/src/styles/tokens.css`, for both themes. `frontend/src/styles/main.css` and the markup only name tokens.
- A colour is named by what it means, never by its hue: the top of `frontend/src/styles/tokens.css` says whose each is.
- A utility never overrides what a `cr-` class sets on the same element: change it with another `cr-` class, or use the utility in place of the class.
- Markup carries no `style="…"` and no `z-` utility: a number only a component knows reaches the stylesheet as `style:--cr-name`, and a layer is a token.
- What scrolls down the page is a `cr-scroller`, never a box a utility makes scroll. It is the box its contents are placed in, so words kept for a screen reader (`sr-only`) scroll with the rest and never stretch the page.

## Panes and keys

- A menu or a pane opened from a control is a `Popover`, its look a `PopoverPanel`.
- A modal is a `Dialog`, closed with `close()` and never by no longer drawing it, so the browser gives the keyboard back.
- A key the review answers is a row of `KEYMAP` in `frontend/src/lib/components/keymap.ts`. A key of one view alone is a row that names its `views`, never a check in a handler.
- Whatever reads keys an editable field can send asks `isComposingText` first: a key building a word in an input method is never the page's.
- When something is put away, sent or removed, what remains takes the keyboard (`focusWhatRemains`): it is never left on nothing.

## Moving the reader

- Whatever takes the reader to a thread or a file — a chip, a notice's list, a key — asks the `Navigator` and widens nothing itself.
- Only the page's own ways through what is read go there directly: a file picked in the tree or in a story's contents to `FileSections`; a part of a story, picked in its contents or its chapter bar, to `ReadingParts`.
- A component asks which view is on screen by its name (`review.views.onScreen.name === 'files'`), never by what it is not.
- Only the switch in the header writes how the reader chose to read (`choose`). Taking them to something only the files draw changes what is on screen (`showFiles`) and leaves the choice alone.
- What hangs on a line's number — a thread, a comment being written — is drawn and taken only where the `Numbering` is the review's own.
- A section that draws lines of a file is a `LinesSection`, whichever view draws it.

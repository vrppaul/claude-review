---
paths:
  - "frontend/**"
---

# The page

How a part of the page is built is said at the top of its module; what eslint and stylelint refuse, and why, in `frontend/eslint.config.js` and `frontend/stylelint.config.js`.

## Types and state

- The page draws what the server says: a rule that decides from the review's state (what counts, what is stale, where a thread hangs) is the server's. The page keeps layout, what is in sight, keys, focus, scroll, the draft.
- Svelte 5 runes; TypeScript in strict mode, no `any`.
- To the compiler a value read from a list or a table by position or key may be missing. Build so that holds, never check around it: a line carries its markup, not a list beside it.
- A place the reader is at is the thing they are at (an id), not its position in a list that changes.
- Find, walk or pair things; reach for an index only where the position is the meaning.
- A function an interface asks for is written as a property (`label: (anchor: Kind) => string`), so the compiler holds it to its parameter types.
- A component's module script exports nothing another module imports: eslint reads a `.svelte` import only through Svelte's catch-all declaration. A type or a function others use lives in a `.ts` module.
- A callback handed to a child component or to `<svelte:window>` names its parameter's type; svelte-check holds it to the prop.
- An object or array only ever replaced whole — what the server sent, a list rebuilt with `map`, `filter` or a spread — is `$state.raw`: deep `$state` wraps every line of a diff in a proxy.

## Parts and elements

- Every kind of element the page draws — a button, a field, a pane, a notice, a mark, a list's row — is a part of `frontend/src/lib/ui/`, whose file says what it is for.
- A kind the library lacks is added there first, with the variants the page uses now and an eslint rule refusing it elsewhere, where a pattern can tell it.
- The parts of `frontend/src/lib/` build on each other in one direction, as `LAYERS` in `frontend/eslint.config.js` lists them: components build on everything, and only components build on them.
- The page's own code never finds an element by test id or by a page-wide id. An element announces itself to whoever needs it, as every file section and thread does to `FileSections`.
- A selector that cannot be avoided reads a `data-role`, or one of two attributes that say which of many an element stands for: `data-place`, the line a line number is, and `data-tour`, the name the tour lights a place by.
- Every new container gets a `data-testid`; a part of the library takes its own as `testId`.
- Markup a library draws (mermaid's `g.node`) is read by the library's names in the module that calls it, and gets its test ids there by `setAttribute`.
- A change to what the reader sees is looked at in a browser, in each theme and width it can differ in, before it is called done: in the report, never in a test.

## Styling

- A colour, a layer or a shadow is written once, in `frontend/src/styles/tokens.css`, for both themes. Every other stylesheet and the markup only name tokens.
- A colour is named by what it means, never by its hue: the top of `frontend/src/styles/tokens.css` says whose each is.
- A utility never overrides what a `cr-` class sets on the same element: change it with another `cr-` class, or use the utility in place of the class.

## Panes and keys

- A menu or a pane opened from a control is a `Popover`, its look a `PopoverPanel`.
- A modal is a `Dialog`, closed with `close()` and never by no longer drawing it, so the browser gives the keyboard back.
- A key the review answers is a row of `KEYMAP` in `frontend/src/lib/components/keymap.ts`. A key of one view alone is a row that names its `views`, never a check in a handler.
- Whatever reads keys an editable field can send asks `isComposingText` first: a key building a word in an input method is never the page's.
- When something is put away, sent or removed, what remains takes the keyboard (`focusWhatRemains`): it is never left on nothing.

## Moving the reader

- Whatever takes the reader to a thread or a file — a chip, a notice's list, a key — asks the `Navigator` and widens nothing itself.
- Only the page's own ways through what is read go there directly: a file picked in the tree or in a story's contents to `FileSections`; a part of a story, from its contents, chapter bar, diagram or chapter chips, to `ReadingParts`.
- A component asks which view is on screen by its name (`review.views.onScreen.name === 'files'`), never by what it is not.
- `choose` writes how the reader chose to read, and eslint holds who may call it. Taking them to something only one view draws changes what is on screen (`showFiles`, `showStory`) and leaves the choice alone.
- What hangs on a line's number — a thread, a comment being written — is drawn and taken only where the `Numbering` is the review's own.
- A section that draws lines of a file is a `LinesSection`, whichever view draws it.

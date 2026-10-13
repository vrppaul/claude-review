# TODO

Roadmap for the review-experience overhaul. Each item is one commit with its
tests. Remove items when done — don't check them off.

## Left from the overhaul

- [ ] `feat(ui)`: mark where a thread would be, in the file it belongs to.
      The bar lists the threads a narrower base cannot draw and takes the
      reader to any of them, so none is stranded — but inside a file that is
      on screen, one hanging on lines this base leaves out shows nothing at
      all. A dashed stub at the top of that file was drawn on the canvas.
- [ ] `feat(cli)`: say what is still waiting on this side. `catch-up` prints
      the whole review as an index; what an agent actually needs between
      turns is the short list — questions asked and not answered, panel
      messages taken and not closed — so it can check itself rather than
      leave a message hanging with a Take back button on it. Found by
      leaving one hanging: answering "first" without naming the message
      never closes it.

- [ ] `perf(review)`: opening a review stages the working tree twice — the
      command line reads the diff from one staging, and the review takes it
      again from another to leave round one's mark. A retake already serves
      what changed, the diff and the new mark from one staging; the opening
      could hand its staging on the same way.

- [ ] `test(ui)`: the base picker has no component test — the filter, the
      three sections, the loading and empty states, the error line, and
      whether a row says its size or its age. Nor do the marks it produces:
      the dot in the tree, the chip in the file header, "Show what changed".

- [ ] `feat(ui)`: let a turn be deleted. A comment can be removed and a
      thread resolved, but a reply — the reader's or the author's — stays
      whatever it says. A duplicate answer has no way out of the thread.

## Bugs

- [ ] `fix(server)`: a review nobody ever opened lives forever. The server
      winds down when the last browser leaves, and "leaves" needs one to
      have arrived: `BrowserPresence` counts the reader gone only once a
      page has opened, so a `--no-open` review whose URL is never opened
      holds its port and ~35 MB until the machine is rebooted. Twelve of
      them were found running at once. Give an unopened review a deadline
      of its own.

- [ ] `fix(cli)`: three usage errors print what the command was handed as
      it was written — a field's name from the story's document, the text
      given for `--lines`, the story file's path — so a terminal's control
      sequence in any of them reaches the terminal. Whatever the reader or
      the repository wrote goes through `terminal_text`; what the agent
      hands a command does not.
- [ ] `fix(cli)`: a value the review's own rule refuses is said with
      pydantic's "Value error, " before the review's words: "Value error,
      says nothing", "Value error, the range runs backwards", and the same
      before a story's lines that name none.
- [ ] `fix(cli)`: `point --lines 0` says "Input should be greater than or
      equal to 1" twice, once for each end of the range.
- [ ] `fix(ui)`: `]` pressed twice with the keyboard on a line goes to the
      same section twice. The section the reader is in is the one holding
      the keyboard before the one in view (`FileSections.current`), and a
      jump moves the screen and leaves the keyboard where it was. `[` the
      same. Read in the code, and seen in a browser by the second review
      of the story's page.
- [ ] `fix(ui)`: `k` brings the line above to the top edge of the reading
      area, under its file's sticky header (`dom/keyboard.ts`,
      `moveByLine`). Read in the code, not looked at in a browser.
- [ ] `fix(ui)`: a file the page was taking the reader to stays the one
      being read after a thread in another file took them instead — a
      file shown, then `n` before the glide ends — until the reader
      scrolls on: the band is handed back once they are at rest, and
      nothing crosses it until they move (`dom/reading-band.svelte.ts`).
      Read in the code, not looked at in a browser.

## The story, from the reviews of its server side

- [ ] `fix(cli)`: `story` says "0 lines not in the story (docs/logo.png)" of
      a file the change shows no line of — binary, too large, only moved.
      Say such a file apart from lines left out.
- [ ] `test(cli)`: `render_story_taken` has no unit test of its own: it is
      reached only through the command.
- [ ] `docs(story)`: `PlacedFile.left_out` takes runs that share no row —
      the story's checks refuse a line told twice before it is asked — and
      does not say so.
- [ ] `test(wire)`: nothing holds the anchors of `LINES_WRITTEN`. The review
      reads lines with `fullmatch`, so only the API's schema needs them,
      which reads a pattern as found anywhere in a text: with either anchor
      gone, every unit and integration test passes.
- [ ] `refactor(story)`: `ReviewStory.tell` calls the module's `tell`: one
      name for two things in one file.
- [ ] `refactor(story)`: in `story_lines_told.py`, `told` names a run of
      lines in `ToldOfRun.tell` and the tree of them in `first_met`.
- [ ] `test(story)`: the test that a story is told off the event loop waits
      three turns of the loop and then looks. That the telling runs in
      another thread is the fact, and a test of that needs no count.
- [ ] `refactor(story)`: a told story is frozen, and the rows its pieces
      show are the take's own `DiffLine`s, which are not.
- [ ] `feat(story)`: a story's steps do not follow the code when the diff
      is taken again: the whole story is read as the code was, and takes
      no comment, until the agent tells it again. And the agent is not
      told its story is stale.
- [ ] `fix(story)`: a story told while the working tree has moved on from
      the take on screen is checked against the take, and nobody is told.
- [ ] `fix(cli)`: `story` prints every file it left out on its one line.
- [ ] `docs`: the switch to a story is offered in every review of a
      change, and neither the skill nor the README tells an agent to tell
      one.

## The story, on the page

- [ ] `feat(ui)`: a chapter's head says how many steps tell it, where the
      canvas says its files too: "3 files · 4 steps".
- [ ] `feat(ui)`: a piece of a file told in two chapters does not say so:
      the canvas draws "also in chapter 1" in its head.
- [ ] `feat(ui)`: each view opens at its top when the reader switches back
      to it. `FileSections.readingPlace` / `returnTo` name a section by
      its key and can carry the place.
- [ ] `feat(ui)`: a story has no contents beside it: the canvas draws its
      chapters down an axis, each with its files, and marks the one read.
- [ ] `fix(ui)`: when the whole review cannot be put back for a thread or
      a file the reader asked for, the files come on screen and the bar
      says why, and the keyboard is left on nothing.
- [ ] `fix(ui)`: a story the code has moved on from still lists Enter and
      n / p in its help, which do nothing in it.
- [ ] `refactor(ui)`: whose numbers a drawing's lines carry is named
      `'the-reviews'`, `'a-narrower-bases'`, `'another-takes'`
      (`anchors/numbering.ts`): possessives with the apostrophe gone, and
      the last reads as a plural where it is compared.
- [ ] `refactor(ui)`: a failed request for a diff is said three ways: an
      `Attempt` in two notices, `changedSinceFailed` in `FileSection`, and
      what the diff itself keeps of the whole review not put back.

## Infrastructure

- [ ] Submit to the official Claude Code plugin marketplace
- [ ] `line_span(start, end)` takes two numbers where `lines_named` gives
      back a `LineSpan`, so two callers take a `LineSpan` apart to say it:
      one shape, written twice.
- [ ] Move file reading out of `FileWindowService` and `read_text_files`
      (`services/text_files.py`) into `repositories/`, behind interfaces, the
      way `ImageService` keeps policy and `DirectoryImageStore` touches the
      disk. Both read files themselves today.
- [ ] `refactor(ui)`: a column's width, its least and its most, and
      `setWidth` are written out twice in `reader/page-layout.svelte.ts`:
      for the file tree and for the agent panel.

## Testing

- [ ] Drop `tmp_path` from unit tests — services should accept data in memory
      so unit tests don't touch the filesystem
- [ ] The Python tests hold 138 branches in 28 files — an `if`, a
      conditional expression, an `or`, a filter in a comprehension — where
      the owner's rule for tests is that a test and its helpers hold none:
      one case to a property, inputs made by construction. The two files
      that hold the most are `tests/unit/test_unified_diff.py` (28) and
      `tests/helpers.py` (25). The page's tests hold branches too, and are
      not counted here.
- [ ] A page test that asks what `document.activeElement` says, by its
      text, passes with the keyboard on the page itself, which says
      everything; and a spy on an element's `scrollIntoView` is the one
      every element shares. Four such assertions, and the spies of the two
      tests of `]` and `[`, were put right; one spy is left, in
      `frontend/tests/push-handling.test.ts`, and the rest of the page's
      tests were not searched for the first.
- [ ] Lines of the page that can be broken with every test passing, found
      by an independent review: the classes `cr-file-frame` and
      `cr-file-placeholder` in a section (`LinesSection.svelte`: what is
      left undrawn off screen, and the room a section holds before its
      rows are built); going to a thread already drawn ending the wait for
      a section (`dom/file-sections.ts`, `goToThread`); `rowOf`'s "past
      the last row" (`anchors/placement.ts`); `chapterNamed` as any one
      chapter (`components/story-words.ts`); the guard for a review
      compared against nothing in `ReviewDiff.showWholeReview`.
- [ ] eslint's rule for a utility that makes a box scroll down reads the
      named values alone: one written in place, `overflow-y-[auto]` or
      `[overflow-y:auto]`, is let through. The page writes neither.
- [ ] Nothing holds the finish pane, the mention list and the panel's
      conversation to being `cr-scroller`s: with the class taken off any of
      the three every browser test passes, since none has a pane longer
      than its box.
- [ ] `RequestPart.QUERY` and `RequestPart.PATH`
      (`src/claude_review/presentation/wire/refusal.py`) are named by a
      test alone, `tests/unit/test_refused_fields.py`: the package matches
      them by value.
- [ ] Older tests make a variant of a model with `model_copy(update=…)`,
      its fields named in text: seven in `tests/unit/test_cli_rendering.py`,
      two in `tests/integration/test_session_socket.py`.

## Known limits

- A file the agent shows far down the review is glided to, and then put in
  place at once: the glide ends where the file stood before the files on
  the way were built, and what is left to go is not glided. Showing the
  last of 46 files, that was 446 pixels. A glide that far also builds every
  file it passes.
- A single generated file of ~12,000 lines takes about 2.6s to become
  readable, because a file is built as one unit. Splitting a hunk into
  separately contained blocks was measured and made it worse. Worth
  revisiting only if such files turn up in real reviews.

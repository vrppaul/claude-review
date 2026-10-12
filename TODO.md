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

## The story, on the page

- [ ] `refactor(ui)`: a story's piece writes a section's shell beside the
      files' own — how many rows it will draw, its announcing itself to the
      page, its being built when near, the header's classes, the
      placeholder. One component for "a section of a file's lines", used by
      `FileSection` and `StoryPiece`.
- [ ] `refactor(ui)`: `StoryView.svelte` draws every part of a story in one
      component, and says the agent's edge as utilities five times. The
      agent's words are one block; the overview, a chapter, a step and what
      was left out are parts. Asking about a block and a thread under it
      will hang on that block.
- [ ] `fix(ui)`: a step has no heading, two steps of one file give the same
      one, a chapter's and a step's number stand outside their headings,
      the overview's labels are spans, and a piece says its file's status
      as a bare letter.
- [ ] `refactor(ui)`: a story's sections are known by their place
      (`step:<chapter>:<step>`, `left-out:<n>`), which is another step's
      once a story is told again. A step has an identity: its file and
      first line, since a line is told once.
- [ ] `perf(ui)`: `StoryReading` builds the list of a story's pieces again
      on every question, and looks a thread's line up by walking them. An
      index of the story held, built once. Its `Standing` and `standingOf`
      are a second copy of those in `anchors/placement.ts`.
- [ ] `test(ui)`: much of what a story says is held by no test: its task,
      its doubt, a chapter's why, a step's lines, the counts of steps and
      of housekeeping files, the paragraph of a reconstruction, the round
      where it is not the first, a piece's status letter and counts, a
      piece left unbuilt until it is near, and which piece is being read.
- [ ] `test(ui)`: the test that a thread is drawn in one piece picks the
      pieces that draw it with a `.filter`, a branch in a test.
- [ ] `feat(ui)`: each view opens at its top when the reader switches back
      to it. `FileSections.readingPlace` / `returnTo` name a section by
      its key and can carry the place.
- [ ] `feat(story)`: a story's steps do not follow the code when the diff
      is taken again: the whole story is read as the code was, and takes
      no comment, until the agent tells it again. And the agent is not
      told its story is stale.
- [ ] `fix(story)`: a story told while the working tree has moved on from
      the take on screen is checked against the take, and nobody is told.
- [ ] `docs`: the switch to a story is offered in every review of a
      change, and neither the skill nor the README tells an agent to tell
      one.
- [ ] `fix(cli)`: `story` prints every file it left out on its one line.

## Infrastructure

- [ ] Submit to the official Claude Code plugin marketplace
- [ ] `line_span(start, end)` takes two numbers where `lines_named` gives
      back a `LineSpan`, so two callers take a `LineSpan` apart to say it:
      one shape, written twice.
- [ ] Move file reading out of `FileWindowService` and `read_text_files`
      (`services/text_files.py`) into `repositories/`, behind interfaces, the
      way `ImageService` keeps policy and `DirectoryImageStore` touches the
      disk. Both read files themselves today.

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
- [ ] Older tests make a variant of a model with `model_copy(update=…)`,
      its fields named in text: seven in `tests/unit/test_cli_rendering.py`,
      two in `tests/integration/test_session_socket.py`.

## Known limits

- A single generated file of ~12,000 lines takes about 2.6s to become
  readable, because a file is built as one unit. Splitting a hunk into
  separately contained blocks was measured and made it worse. Worth
  revisiting only if such files turn up in real reviews.

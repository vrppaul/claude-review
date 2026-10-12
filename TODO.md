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

## The story, from the reviews of its server side

- [ ] `fix(cli)`: the story file's usage error prints the document's field
      names as they were written, so a key holding a terminal's control
      sequence reaches the terminal. Everything else the reader or the
      repository wrote is printed through `terminal_text`.
- [ ] `fix(cli)`: `story` says "0 lines not in the story (docs/logo.png)" of
      a file the change shows no line of — binary, too large, only moved.
      Say such a file apart from lines left out. `render_story_taken` has no
      unit test of its own.
- [ ] `fix(cli)`: two refusals read badly. A step's lines that name no lines
      are refused with pydantic's own "Value error, " before the review's
      words; `point --lines 0` says "Input should be greater than or equal
      to 1" twice, once for each end of the range.
- [ ] `docs(story)`: `PlacedFile.left_out` takes runs that share no row —
      the story's checks refuse a line told twice before it is asked — and
      does not say so.
- [ ] `test(wire)`: nothing holds the anchors of `LINES_WRITTEN`. The review
      reads lines with `fullmatch`, so only the API's schema needs them,
      which reads a pattern as found anywhere in a text: with either anchor
      gone, every test passes.
- [ ] `test`: older tests make a variant of a model with
      `model_copy(update=…)`, which the package no longer does —
      `tests/unit/test_cli_rendering.py` (seven) and
      `tests/integration/test_session_socket.py` (two) — and four helpers
      of `tests/unit/test_cli.py` hold a branch (`_repeated`,
      `_offered_commands`, `_every_command`, and the test that every
      command takes its values by name).
- [ ] `refactor`: `line_span(start, end)` takes two numbers where
      `lines_named` gives back a `LineSpan`: the two are one shape, said
      twice.

## Infrastructure

- [ ] Submit to the official Claude Code plugin marketplace
- [ ] Move file reading out of `FileWindowService` and `read_text_files`
      (`services/text_files.py`) into `repositories/`, behind interfaces, the
      way `ImageService` keeps policy and `DirectoryImageStore` touches the
      disk. Both read files themselves today.

## Testing

- [ ] Drop `tmp_path` from unit tests — services should accept data in memory
      so unit tests don't touch the filesystem

## Known limits

- A single generated file of ~12,000 lines takes about 2.6s to become
  readable, because a file is built as one unit. Splitting a hunk into
  separately contained blocks was measured and made it worse. Worth
  revisiting only if such files turn up in real reviews.

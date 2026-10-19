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

- [ ] `build(page)`: `pnpm build` warns of a chunk over 500 kB: mermaid's
      langium parsers (630 kB), fetched only by the kinds of diagram mermaid
      parses with them (architecture, git graphs and others), never by a
      flowchart. Leave them out of the build if mermaid lets it be done
      cleanly, as elkjs is; the warning's limit is not raised to hide it.

- [ ] `feat(ui)`: let a turn be deleted. A comment can be removed and a
      thread resolved, but a reply — the reader's or the author's — stays
      whatever it says. A duplicate answer has no way out of the thread.

## Bugs

- [ ] `fix(server)`: two reviews running at once can lose one another's
      change to a record about the reader. The lock that makes changes to
      a record one after the other is each review's own
      (`ReaderRecordService._changing`), and every review is a process of
      its own: one keeping the release a reader was shown while another
      keeps that Story was introduced can both read `guide.json` before
      either writes, and the second puts back what the first changed. The
      settings, several choices in one file, have the same gap.

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
      area, under its file's sticky header, and deep in a chapter of a
      story under the chapter's bar too (`dom/keyboard.ts`, `moveByLine`).
      Read in the code, not looked at in a browser.
- [ ] `fix(ui)`: a file the page was taking the reader to stays the one
      being read after a thread in another file took them instead — a
      file shown, then `n` within the frames before it comes to rest —
      until the reader scrolls on: the band is handed back once they are
      at rest, and nothing crosses it until they move
      (`dom/reading-band.svelte.ts`).
      Read in the code, not looked at in a browser.

- [ ] `fix(ui)`: what the browser noted of a section before it was taken
      back, and says after, is counted as crossing the band where the
      section still stands on the page, and stays counted until the area is
      watched anew (`dom/crossing.ts`): no file is then said to be read
      while that section comes first of those counted. Read in the code,
      not seen in a browser.

## The story, from the reviews of its server side

- [ ] `fix(cli)`: `story` says "0 lines not in the story (docs/logo.png)" of
      a file the change shows no line of — binary, too large, only moved.
      Say such a file apart from lines left out.
- [ ] `docs(story)`: `PlacedFile.left_out` takes runs that share no row —
      the story's checks refuse a line told twice before it is asked — and
      does not say so.
- [ ] `test(story)`: the test that a story is told off the event loop waits
      three turns of the loop and then looks. That the telling runs in
      another thread is the fact, and a test of that needs no count.
- [ ] `refactor(story)`: a told story is frozen, and the rows its pieces
      show are the take's own `DiffLine`s, which are not.
- [ ] `fix(story)`: a story told while the working tree has moved on from
      the take on screen is checked against the take, and nobody is told.
- [ ] `fix(cli)`: `story` prints every file it left out on its one line.
- [ ] `feat(story)`: a step of a file renamed between two takes stands
      nowhere: the diff between them finds the rename, and nothing follows
      the step to the new name.

## The story, on the page

- [ ] `fix(ui)`: a story the reader asks for by hand whose request fails
      is said in the panel and nowhere else. The page goes on holding no
      asking, and the story view goes on saying "Asking the agent for a
      story", with the files as the one way on (`StoryWaiting.svelte`).
- [ ] `fix(ui)`: a story the page reads only as it catches up, told in a
      gap the review could not hand over, is held and never offered under
      the switch: the page notes a story as arrived unseen only where it
      heard it being told (`ReviewStory.readAnother`).
- [ ] `fix(ui)`: at 420 pixels the reading area stands one pixel lower
      while the Story segment says "writing" than while it says "Story":
      the dots that breathe in place of its icon make the header's first
      row a pixel taller. Measured by an independent review, in a look.
- [ ] `fix(ui)`: at 420 pixels the reading area is 789 pixels tall in Files
      and 821 in Story: the header wraps a third row in Files, for the base
      picker, so a switch between the views moves the reading area 32
      pixels. Measured by an independent review, in a look.
- [ ] `feat(ui)`: each view opens at its top when the reader switches back
      to it. `FileSections.readingPlace` / `returnTo` name a section by
      its key and can carry the place.
- [ ] `fix(ui)`: deep in a chapter, the step its bar and the contents say
      is being read changes late. The band that says which section is read
      begins at the top of the reading area (`dom/reading-band.svelte.ts`),
      behind the bar: a piece whose last rows are behind the bar is still
      the one read. Read in the code, not looked at in a browser.
- [ ] `feat(ui)`: a step the reader is taken to stands right under the bar
      of its chapter, or under the page's header, with no room above its
      reason.
- [ ] `refactor(ui)`: what is being read has three names: `fileInView` and
      `sectionInView` in `FileSections`; `beingRead` in `ReadingParts` and
      in what keeps whatever announced itself for both
      (`dom/announced.ts`); and `earliest` in the band they are read in
      (`dom/reading-band.svelte.ts`).
- [ ] `fix(ui)`: when the whole review cannot be put back for a thread or
      a file the reader asked for, the files come on screen and the bar
      says why, and the keyboard is left on nothing.
- [ ] `fix(ui)`: a button of a chapter's bar that goes while the bar stays
      drops the keyboard it holds. The bar hands the keyboard on only when
      the whole of it goes (`ChapterBar.svelte`); the way to the chapter
      after goes alone when the reader is at once deep in the last chapter,
      no head having crossed the screen. Seen in a browser: the keyboard
      on that button deep in chapter 2 of 3, the area scrolled at once to
      deep in chapter 3, and the keyboard is on the page itself.
- [ ] `fix(ui)`: a line key pressed with the keyboard on a button that is
      kept in sight counts from where the button stands in the document,
      not on screen (`steppedTo`, `dom/keyboard.ts`): from a chapter's bar
      it lands on the first line of the story, and from a file's header
      kept over the middle of its file, on that file's first line. Read in
      the code, not looked at in a browser.
- [ ] `fix(ui)`: in a review that is over, the agent panel put away by its
      own button leaves the keyboard on nothing: the header then draws no
      control to take it (`ReviewHeader.svelte`).
- [ ] `refactor(ui)`: whose numbers a drawing's lines carry is named
      `'the-reviews'`, `'a-narrower-bases'` (`anchors/numbering.ts`):
      possessives with the apostrophe gone.
- [ ] `refactor(ui)`: where a thread hangs is said twice: `#hangsHere` in
      `components/line-commenting.svelte.ts`, over the lines a drawing
      places, and `fileDraws` in `anchors/placement.ts`, over the diff's
      rows, for the narrower base's notice and the story's pieces. They
      differ on the old number of a kept line, which the diff's rows carry
      and a drawing places on the new side only: `fileDraws` counts a
      thread on it as drawn, and it hangs under no line of the drawing.
- [ ] `refactor(ui)`: a failed request for a diff is said three ways: an
      `Attempt` in two notices, `changedSinceFailed` in `FileSection`, and
      what the diff itself keeps of the whole review not put back.

## The page's look, for later

The owner's list of 2026-10-15, after the story's UI round ("потом"): none
of it is built yet.

- [ ] `feat(ui)`: a new look for the agent's progress in its panel.
- [ ] `feat(ui)`: a new look for a folded thread's line (its words are in
      the code's face today).
- [ ] `feat(ui)`: a new look for the rows of the tree of files, and a new
      design of the tree itself.
- [ ] `feat(ui)`: a new look for the buttons under a comment being written
      and the line of keys under them.
- [ ] `feat(ui)`: a new look for a chapter's frames: its warning, its why
      and where to doubt it.
- [ ] `feat(ui)`: a new look for the "also in chapter N" chip.
- [ ] `feat(ui)`: a new look for the line that says who wrote a thread's
      turn and when.
- [ ] `feat(ui)`: a new look for the arrows.
- [ ] `feat(ui)`: every chip, looked at again.
- [ ] `feat(ui)`: animations.
- [ ] `refactor(ui)`: one kind of dialog everywhere, the agent's panel
      included.

## The page's library, what its steps left

- [ ] `refactor(ui)`: four components still draw a `<button>` of their own
      — the gutter, the hunk gap's ways, the reply field, the folded line —
      named with the part that is to take each in `STILL_PRESSED_BY_HAND`
      (`frontend/eslint.config.js`); eslint refuses one everywhere else.
- [ ] `refactor(ui)`: what every gate still lets through: a quiet or done
      notice bar on base-200; an opacity form such as `bg-warning/10` (a
      colour `tokens.css` never wrote); a mark whose corner and ground are
      split over two strings, or over a class and a stylesheet rule; a role
      or an element in a spread of attributes; a mark, a question or a
      heading drawn by `main.css` or by utilities; the stylesheet's round
      drawings (avatars, a story's nodes); the story contents' axis laid
      out in `main.css` from Row's tokens; utilities held in a script's
      string and handed to `class={…}`, which no gate of a class list
      reads. A rule that each look class has one owner is to hold them.
- [ ] `feat(ui)`: whether a pane keeps its side while the page scrolls under
      it: one now opens the other way the moment it stops fitting.
- [ ] `feat(ui)`: whether a notice other than a broken part's announces
      itself (`role="status"`), and whether the end of a review, a notice
      like any other since `8fae66a`, should stand out more.

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
      for a column the reader puts away (`PutAwayColumn`) and for the
      agent panel.
- [ ] `refactor(server)`: three routes call two methods of the `Review`
      where the rule is that a route calls one (`.claude/rules/wire.md`):
      GET /api/review (`presentation/routes/page_routes.py:80-81`), GET
      /api/diff (`177-178`) and GET /api/versions (`190-191`).
- [ ] The instruction-files gate reads a path only between two backticks
      on one line of prose (`scripts/check_instruction_files.py`): a path
      inside a fenced block, or one a Markdown link points at, is not held
      to being there.
- [ ] A file of instructions the reader may not open ends the
      instruction-files gate in an exception, `PermissionError`, where one
      that is a directory, a link to nothing or not UTF-8 is a fault said
      by name (`_read`, `scripts/check_instruction_files.py`).
- [ ] A script stopped while Python is still loading it ends by the signal,
      143 to a shell, where its docstring promises 130 from its own first
      line on: measured of a look, SIGTERM 0.03 s and 0.08 s after its
      start, against 130 from 0.11 s. It has made nothing by then. Hearing
      the signal sooner means a statement before the imports, which ruff
      refuses (E402), or imports inside a function (PLC0415).
- [ ] On Windows, a checkout without `core.symlinks` writes `CLAUDE.md` as
      a one-line file where it is a link to `AGENTS.md`, and the
      instruction-files gate (`scripts/check_instruction_files.py`) fails
      there.
- [ ] Before a release, decide whether `CLAUDE.md` and `.claude/` are left
      out of the sdist, which leaves out `/frontend` alone: whether PyPI
      takes an sdist that holds a symlink is not checked.
- [ ] `perf(server)`: GET /api/diff and GET /api/story build and write
      their whole body on every request, on the event loop: 7.3 and 5.0 ms
      for the change `scripts/long_change.py` makes (41 files), 45.7 and
      43.5 ms for ten of it (410 files), about 17 ms a MB. Writing each
      body once as it changes pays only for changes far larger.
- [ ] `perf(cli)`: every agent command loads `services/image_service`, and
      structlog with it, through `presentation/wire/base.py`: about 71 ms
      of an import of some 245 ms, `wire/agent.py` about 149 ms in all
      (`python -X importtime`, one run).
- [ ] `refactor(hosting)`: `hold_open` (`hosting/serving.py`) makes a
      `GitRepository` for every kind of review and hands it to
      `host_review`, where only a review of a change reads it
      (`content_source`): a review of files or of a conversation is made a
      git reader it never calls. Making one only for a change would choose
      the source by kind in two callers, `serving.py` and the tests'
      `hosted` (`tests/helpers.py`), unless the choice moves with it.
- [ ] `refactor(wire)`: `StoryTakenResponse.summing_up` builds its
      `LeftOutOfFile`s field by field (`presentation/wire/story.py`), not
      with `.of()` from a domain twin as wire.md asks of every wire model.

## Testing

- [ ] `test_whatever_a_route_is_sent_it_answers_as_its_schema_says`
      (`tests/integration/test_api_schema.py`) failed once for `POST
      /api/anchors/follow`, in a run of every test at `3090d46`, and passed
      in the six runs of it that followed, one of them of every test again.
      Schemathesis draws its requests anew each run, and the request that
      failed was not kept.
- [ ] `page_reading_the_story` (`tests/integration/test_story.py`) puts a
      `Review` together by hand, not through `host_review`, against
      server.md's one place for it: the pages it stands for read the story
      as each event is told, and the broadcast `host_review` makes queues
      what it tells.
- [ ] A review leaves in its event loop what nothing ends. The answerer's
      lease is a timer of ten minutes (`Answerer.heard`,
      `src/claude_review/services/review/answerer.py`) that outlives the
      review. A server that cannot listen leaves uvicorn's lifespan task
      pending: `test_a_server_that_cannot_listen_ends_the_review_and_says_it_never_came_up`
      (`tests/integration/test_review_server.py`) ends with it. One process
      serves one review, and such a test has a loop of its own that takes
      both away. The browser tests share one loop: 37 of the 101 left a
      lease in it when counted, which `nothing_left_running`
      (`tests/e2e/conftest.py`) cannot see, for it sees tasks. A lease left
      there fires only if browser tests are still running ten minutes on.
- [ ] A look serves one change (`scripts/look.py`), so a diff of no file
      cannot be looked at with it, and the review's command line serves no
      such diff either: the page reaches one only when a change is undone
      under a review being served and the diff is taken again. The help
      over one was looked at by hand, so.
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
- [ ] eslint's rule for a utility that makes a box scroll down reads the
      named values alone: one written in place, `overflow-y-[auto]` or
      `[overflow-y:auto]`, is let through. The page writes neither.
- [ ] `RequestPart.QUERY` and `RequestPart.PATH`
      (`src/claude_review/presentation/wire/refusal.py`) are named by a
      test alone, `tests/unit/test_refused_fields.py`: the package matches
      them by value.
- [ ] Older tests make a variant of a model with `model_copy(update=…)`,
      its fields named in text: seven in `tests/unit/test_cli_rendering.py`,
      two in `tests/integration/test_session_socket.py`.
- [ ] Five test modules write `STORY_ROUTE` themselves, and
      `tests/integration/test_story.py` the routes a story is asked for and
      stopped at, where `tests/helpers.py` names all three; and the change
      a story is told of, with the steps that tell it, is written in two
      (`tests/integration/test_story.py`, `test_agent_commands.py`).
- We need to add the acknowledged status - when the agent received the event and sent back the event that acknowledged. This can be done via mods
- We need to add a way for the agent to reply to the whole thread and let the server to post the proper ordering
- We need to add a way to retract the message if needed or to modify it
- We need to add a rule that all messages from the agent should be concise and well markdown formatted
- For some reason all agents see --no-open, it should not be the default
- CHanging the base must not mean restarting
- keeping the loop running is the boilerplate - from one of the agents
- add a way to report a bug/suggest an improvement

## Known limits

- A part of a story is read through once scrolling carries its end into
  view or out above the top, and no time is counted: a jump across a whole
  chapter (`n`, `p`, a file the agent shows, a part picked in the
  contents) ticks it.
- What the reader has read of a story is forgotten when the page hears the
  story was told again. A story told again in a gap the review could not
  hand over is read as the page catches up, and its ticks stay: they stand
  for the parts of the new story known by the same names.

- A file or thread the page takes the reader to is scrolled to at once,
  and once more three frames later, when the files beside it stand at their
  real size: counted, since nothing says when all of them are built, and
  seen in Chromium only. A section holds the room its rows, hunk headers
  and bars take, not a thread's card (about 155 pixels), a comment being
  written, or lines and headers that wrap; Chromium's scroll anchoring makes
  up for what grows above only where the file lands at or above the pixel,
  so the second scroll does. If that scroll moves the area up, a file above
  can come into view and grow after it, and nothing follows it.
- A single generated file of ~12,000 lines takes about 2.6s to become
  readable, because a file is built as one unit. Splitting a hunk into
  separately contained blocks was measured and made it worse. Worth
  revisiting only if such files turn up in real reviews.

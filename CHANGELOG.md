# Changelog

## [1.4.0] - 2026-09-10

A round leaves a mark, so the review can be asked what has changed since it.

### Added
- **Choose what the working tree is read against** — the second half of the
  header's title became a control: the base this review opened with, an
  earlier round of it, or any branch or tag. What it changes is what is
  drawn, never what the review holds. The right-hand side of the diff is
  always the working tree, so every thread stays anchored where it was
  written, and one this base cannot draw is hidden and counted rather than
  moved or marked outdated
- **A round leaves a mark** — the tree the diff was taken from is written as
  a real git object each time it is taken. The work under review is
  uncommitted, so between two rounds there may be no commit to go back to.
  The objects live in a store belonging to the review, which goes with it:
  the repository gains nothing, and a restarted server keeps only the refs
- **A retake says what changed** — which files moved since the last one, and
  from which round they are counted. `claude-review round` returns the same
  list, so an agent that came back to a review it left reads those files
  again rather than all of them

### Fixed
- **A file the agent rewrote kept its "viewed" tick** through the retake, so
  a reader walked past code that had changed under them. The tick now comes
  off exactly the files the round moved, and the file is unfolded with it —
  left folded, it reads as read
- **A file the agent pointed at barely said so.** The mark was a background
  behind an opaque file header and rows that paint their own, so it showed
  where nobody was looking. It is an outline now, painted after every
  descendant — and it waits for the scroll to stop, because across sixty
  files a smooth scroll outlasted the mark itself. Shown twice running, it
  flashes twice
- **The notice that the working tree had moved on was said once and lost.**
  It lived only in a push, so a review reloaded at that moment never heard
  it, and one opened later never learned the tree had moved before it
  arrived — the "Retake" it offers went with it. The diff now says how far
  the tree has drifted, so a review that has just loaded knows; what the
  reader waves away stays away until something else moves
- **Work nobody was waiting on could not be shown at all.** The progress line
  was drawn only under an unanswered message and put out by any answer, so
  what an agent did on its own account — working through a round, reading
  with subagents — left the panel looking idle. It now has a row of its own,
  and an answer ends only the work it answers
- **The box being written in and the lines it was about wore one colour.**
  Both are the reader's own mark, but a composer washed in the same tint as
  the rows directly above it read as one patch. The tint now belongs to the
  lines; the composer keeps the edge and stands on the page's own surface
- **The `@@` marker stayed in the middle of the code** once the lines it hid
  had been revealed, announcing a jump where the code ran on unbroken. It
  now belongs to the gap it marks and goes with it — including at the top of
  a file whose first hunk starts at line 1

## [1.3.0] - 2026-09-09

The review gains a second conversation: one about the change as a whole,
with the agent that wrote it.

### Added
- **The agent panel** — a panel on the right for everything a thread is not
  about: the plan, the tests, a file nobody commented on. It reaches the
  same agent that answers the threads, in the same vocabulary — the reader's
  turns on the mark's tint, an answer on the page's own ground, a waiting
  turn that holds its place. Everything typed there goes at once; there is
  one button, because "add to review" has no meaning outside a thread
- **Point at a thread with `@`** — the picker lists the threads with their
  state, and what travels with the message is the thread itself: its lines,
  the comment that opened it and every turn since. The reference is a token
  in the text, so deleting the word takes the reference with it
- **Two numbers, told apart** — what handing this review over costs is
  arithmetic over the diff and the threads, and the review does it. How much
  context the agent has left cannot be measured from here at all, so it is
  quoted with who said it and when, and shown as nothing until it is said
- **Stop a message** the agent is still working on — a request on the same
  queue, not a kill: nothing here can reach into another process
- **A notice when the working tree moves on** — the server polls
  `git status --porcelain` and says how many files have changed since the
  diff was taken. It never swaps the diff by itself: doing that under a
  half-written comment orphans it. After a retake, the bar says what became
  of the threads and offers a way to the one that lost its lines
- **The author can point at a line** — `claude-review point --file --lines`
  raises a thread on the code, for what a paragraph elsewhere would bury:
  where the agent did something other than what was asked, and why. It is an
  ordinary thread from there on, drawn in its own colour because the marks in
  a review are the reader's, and it never counts as their unsent work
- **Progress, while the work is happening** — `claude-review progress` puts a
  live line under the waiting turn: what is being done and which files are in
  hand, replaced as it changes and gone when the answer lands. `--did` and
  `--step` are drawn as branches of the work, so three subagents read as
  three branches rather than as a sentence about three subagents; the files
  are chips the reader can jump by
- **The agent can speak first** — `claude-review say` without `--message` is
  an unprompted message, so work finished while the reader was reading
  arrives on its own, with the dot, the tab count and the optional tick that
  answers already have
- **Jump to a file, or be taken to one** — `say --file` offers the jump;
  `claude-review show --file` takes the reader there and marks the file for a
  moment. The only thing here that moves somebody else's screen, and only
  when they asked
- **Catching up** — `claude-review context` says what a review already
  holds: the round, a line per thread, the panel in short. `wait` hands over
  what happens next and never what already happened, so an agent restarted
  mid-review used to know nothing. An index on purpose; `--thread <id>` gets
  one thread in full
- **The round survives a restarted server** — the review on screen says where
  it had got to when it connects, and never downwards, so a server that came
  back believing it was round one stops numbering the next round wrongly
- **A thread raised on a line that is not in the diff is refused**, with what
  the review does have. It used to be accepted and shown hanging on nothing
- **`@` points at any file**, not only at what already has a thread
- **`c` talks to the agent, `f` shows or hides the tree** — the panel was the
  one thing in the review that needed a mouse
- **The file tree can be dragged narrower or put away**, and the panel's
  width is the reader's in the same way
- **`claude-review say`** answers a panel message by name, and
  **`claude-review status --model --context`** reports what only the agent
  can know. `claude-review wait` now also yields `message` and `cancel`

### Changed
- The panel's conversation, its width and whether it is open live in the
  draft and the reader's preferences, so a reload keeps all three
- "Diff retaken" takes itself away after twelve seconds: it reports something
  that has already happened and wants no answer

## [1.2.0] - 2026-09-09

A comment becomes a thread, and sending stops having to be the end of the
review.

### Added
- **Threads** — a comment carries turns with speakers and a composer under
  the last one, an answer hangs off the question it answers, and asking
  twice no longer overwrites the first exchange
- **Ask from the composer** — "Add to review" keeps the comment with the
  rest and sends it when the review does; "Ask now" hands it over
  immediately and marks it a question. The severity chip stops looking like
  a control that asks
- **Rounds** — with an agent waiting on the review, sending sends a round and
  leaves the review open: the agent answers, makes the changes and retakes
  the diff with `claude-review round`, and the reading carries on. "End
  review" is the separate act that finishes it. A round carries what is new
  since the last one, not the whole review again
- **Threads survive a retaken diff** — a thread whose lines moved follows
  them, and one whose lines are gone is marked outdated and keeps a copy of
  what it was written against. Both travel into the submitted markdown
- **Resolve a thread**, which collapses it to a line and goes out marked
  resolved — the state belongs to the comment, not to the tab
- **A "Replies" list in the header** — answers you have not read, with a
  count, a jump to the thread, `a` for the next one, and an optional tick
  when one lands while the review is in a background tab
- **The tab says so** — the title carries the unread count and the icon takes
  a dot, so an answer is visible from a tab strip
- **An answer lands under the question it answers.** Every question carries
  an id: `wait` hands it over, `reply --question` gives it back, and two
  questions asked before either is answered still read straight. A question
  also carries the whole thread, starting with the comment that opened it
- **Comments and answers are markdown** — code blocks with highlighting,
  lists, inline code, through the renderer that already draws md previews
- **Fold a thread away** with the same control that folds a file, and read a
  folded or settled one by opening it. Resolving folds a thread rather than
  hiding it: settling something no longer means it cannot be read
- **A suggestion is shown as the change it asks for** — the lines it replaces
  above the lines it puts there, marked the way the diff marks them
- **What has already gone out is marked** — a thread sent with a round carries
  a `sent · round N` stamp and gives up the mark colour, and the header counts
  what the answering side has not seen
- `claude-review round`, and `claude-review wait` now also hands over rounds

### Changed
- **A review reopened on the same repository comes back on the same port**,
  derived from the repository and the base ref, so the draft left in the
  browser's storage is still there. `--port` still wins, and a derived port
  someone else holds falls back to a free one
- **Nothing in the interface is named Claude** — whoever answers is whatever
  agent is driving the review, and the wording now says so
- **A comment sits under the side it is about** in the two-column layout, and
  says which side that is in the diff's own signs — the same line number
  exists on both, and a box in the wrong half named neither
- **A comment is measured for reading, not pinched into a column** — the
  measure went from 72 to 96 characters
- **Asking belongs to what it asks about** — the control sits under the last
  thing said in the thread and hands over everything since, while the
  composer's own "Ask now" is about what has just been typed
- **The reader's choices are remembered** — layout, how a markdown file is
  shown, and whether whitespace counts, kept beside the theme. They belong to
  the reader, not to one review, so they survive both
- **A draft written by an older version is brought up to the current shape**
  rather than dropped. The version is there so work can be carried forward —
  losing an hour of reading to a version number is the worse failure

## [1.1.0] - 2026-09-09

A pass over how a review reads and how it is written, plus the beginnings of
a conversation with Claude inside it.

### Added
- **The whole diff as one stream** — every file is on screen at once and the
  sidebar navigates by scrolling to one, so find-in-page, selection across
  files and the reading position all survive moving around
- **Split layout** — the old version faced against the new one, chosen once
  for the review from the header
- **Word-level marking** inside a replaced line, so a renamed identifier or a
  changed constant is visible without comparing two long lines by eye
- **Show the lines a hunk left out**, a screenful at a time or the whole gap
- **Ignore whitespace** — retakes the diff with `-w`, so a reindented block
  stops burying the one line that changed
- **Ask Claude about a comment thread** — the question waits for whoever is
  answering, the reader carries on, and the answer is pushed into the thread.
  `claude-review wait` and `claude-review reply` are the answering half
- **Suggest a replacement** — a comment can carry the code it should become
- **Comment severity** — a question wants an answer before anything changes;
  a blocker has to be dealt with
- **Keyboard** — `j`/`k` between lines, `Enter` to comment, `]`/`[` between
  files, `n`/`p` between comments, `v` viewed, `u` fold, `?` for the list
- **Fold a file, mark it viewed**, filter the tree by path, and see progress
  through a long review in the sidebar heading
- **Comments survive a reload** — an unsent review is picked up where it
  stopped, tied to what was being reviewed
- `--version`

### Changed
- **The server holds the review open on a socket** rather than a heartbeat.
  Browsers throttle timers in a background tab to about once a minute, so
  switching away used to look like an abandoned review: the server exited and
  took the unsent comments with it
- **One palette** for chrome, diff and syntax, replacing a stylesheet that
  imported both highlight.js themes and re-stated forty token colours by hand.
  No syntax colour uses green or red, which belong to the diff
- **A changed row is marked at its edge** over a faint tint, rather than
  washed with colour that dragged every syntax token towards it
- **A comment reads as a note**, not a warning: the mark colour, the reading
  face, one step larger than the code, at a capped measure
- **The header carries the review's identity and actions** — which repository
  and against what — and the bottom strip is gone
- Contrast holds in both themes: every muted token now sits above 4.5:1, where
  light used to lose about a fifth of its contrast to dark
- A hunk is highlighted as a document, so a docstring stays a docstring on
  every one of its lines, and it costs two highlighter calls instead of one
  per line
- A file's rows are built when it comes within reach. A 60-file review of
  3,500 changed lines went from 4.3s to 0.27s before it could be read, and
  from 2.0s to 0.19s to add a comment
- Adds `websockets`, which uvicorn needs to serve a socket at all

### Security
- **The server answers its own page and nothing else.** It had no `Host`
  check, so a page on any domain could point that domain at 127.0.0.1 and
  read the whole working tree and any file in the repository; and the
  same-origin policy never applies to WebSockets, so any page the developer
  had open could connect to the session socket, read what the server pushed,
  and throw away an unsent review by connecting and disconnecting once
- **A previewed markdown file is read, not run.** The preview rendered raw
  HTML out of the repository under review, so `<img onerror>` in a
  contributor's file ran script with the review's own origin — able to read
  the diff, read repository files, and submit comments of its own for an
  agent to act on
- **Expanding context is scoped to the files in the review**, rather than to
  anything in the repository, and no longer names the checkout's location in
  its errors
- **A filename can no longer write its own heading in the review.** Git
  quotes odd paths and the parser decodes them faithfully, so a name
  containing a newline could forge a whole section — a fabricated blocker in
  what the agent reads
- The page states what it may load and refuses to be framed

### Fixed
- **Files with non-ASCII names vanished from the review.** Git quotes such
  paths and the header parser did not expect it, so the file was dropped with
  no warning
- **A renamed file was reported under its old path**, sending the agent to a
  file git had already moved
- **A comment on a removed line appeared twice** and its number was
  ambiguous — `file.py:42` meant either side. Comments now carry the side
- Binary files and permission-only changes said why they had no lines to show
  instead of rendering an empty panel
- A busy port explains itself instead of printing a traceback
- Code no longer breaks mid-identifier when a line is too long for its column
- The composer opens in view when commenting near the bottom of the window
- Reading the diff no longer leaves a git object in the repository for every
  untracked file — 200 files used to leave 1.4 MB behind
- Expanding a hunk's context works from a subdirectory, not only from the
  repository root, and reading a window no longer loads the whole file: a
  134 MB file cost 454 MB of memory and stalled the server for two seconds
- Ignoring whitespace can be turned back off
- A comment appeared twice in the split layout when it sat on an unchanged
  line, and one click on a checkbox killed every keyboard shortcut
- A restored draft could hand out a comment id twice, which made two
  comments edit and delete as one
- Comment navigation reaches a comment in a file whose rows are not built yet
- A summary with no inline comments can be sent from the header, as it always
  could from the dialog
- `wait` and `reply` explain a missing or refusing server instead of printing
  a traceback, and `wait` is told when the review ends
- With `--no-open`, the review's URL is printed rather than left unsaid
- A copied file is shown as a new one, not as a modified one with no lines
- In files mode a file is named the way the reader names it, not by its full
  path

## [1.0.1] - 2026-07-12

### Changed
- **PyPI distribution** — releases are published to PyPI as a prebuilt wheel; installing no longer requires Node/pnpm (`uv tool install claude-review`)
- Skill and plugin install the CLI from PyPI instead of building from the git repo
- Sdist ships prebuilt frontend assets and excludes `frontend/`, so building from sdist needs no JS toolchain
- Release workflow (`release.yml`) publishes on tag push via PyPI trusted publishing (OIDC, no tokens), gated on the full CI suite passing on the tagged commit; publish re-runs are idempotent (`--check-url`)
- `scripts/verify_artifacts.py` — shared artifact verification (self-contained wheel/sdist, version sync across `pyproject.toml`/`plugin.json`, no source maps) used by both CI and release
- Frontend production build no longer emits source maps — cuts the wheel from ~308 KB to ~90 KB

### Fixed
- Build hook now fails loudly when pnpm is missing during a distribution build — previously it silently produced a package with no UI
- Build hook creates `static/dist/` itself when skipping the frontend build on editable installs — CI jobs no longer need the `mkdir` workaround

## [1.0.0] - 2026-04-13

### Breaking
- **CLI subcommands** — `diff`, `files`, `transcript` replace flat `--files`/`--transcript` options. Subcommand is now required (e.g. `claude-review diff` instead of `claude-review`).

### Added
- **`--base` option** — compare changes since a specific commit (`claude-review diff --base HEAD~3`)
- `/review-ui diff --base <commit>` — review changes since a specific commit from the skill

## [0.6.0] - 2026-04-13

### Added
- **Markdown preview** — three content view modes for markdown files: Raw (default), Preview (rendered), Side by side (raw + rendered)
- `ContentViewToggle` — toggle buttons in DiffView header, visible only for markdown content
- `MarkdownRenderer` — renders markdown via `marked` with highlight.js code block syntax highlighting
- `PreviewView` — full rendered markdown with comment count badge
- `SideBySideView` — split pane with synced scroll, commenting via left pane
- `RawView` — extracted from DiffView for reuse in side-by-side mode
- `@tailwindcss/typography` — prose styles for rendered markdown (headings, tables, code blocks, lists)
- 7 E2E tests for markdown view modes (toggle, preview, side-by-side, commenting, persistence, badge, non-markdown)
- 12 new frontend unit tests (store, toggle, renderer, DiffView mode switching, comment badge)

### Changed
- DiffView refactored to thin dispatcher: sticky header + mode-based component routing
- `contentViewMode` stored globally in diffStore, persists across file navigation, resets on `clear()`

## [0.5.0] - 2026-04-13

### Added
- **Transcript mode** — review Claude Code conversation transcripts (`claude-review --transcript conv.jsonl`)
- `/review-ui transcript` — review the current session's conversation
- `TranscriptService` — parses Claude Code JSONL files, merges consecutive turns, filters tool calls and thinking blocks
- `TranscriptReviewService` — formats transcript comments as self-contained blockquote markdown
- Messages shown newest-first with timestamps in sidebar labels
- 28 new tests (unit, integration, E2E, frontend) for transcript mode

### Changed
- Services instantiated in route handlers instead of stored on `app.state`
- `ServerState` moved from `schemas.py` to dedicated `state.py` module
- CLI uses single `asyncio.run()` instead of two separate event loops
- Heartbeat timeout extracted to `HEARTBEAT_TIMEOUT` module constant

## [0.4.2] - 2026-04-12

### Added
- Component tests for CommentBox, ReviewModal, DiffView, FileList, SubmitBar (19 tests)
- Frontend pre-commit hooks — ESLint, svelte-check, Prettier (skip gracefully if pnpm not installed)
- `svelteTesting()` plugin for client-side component mounting in vitest
- `data-testid` on comment count, cancel buttons, and all remaining interactive elements

### Changed
- Clarified test selector convention in AGENTS.md: testids for interaction, getByText for visible content assertions

## [0.4.1] - 2026-04-12

### Added
- Review mode badge in bottom bar (Diff / Files / Transcript)
- `data-testid` attributes on key interactive elements for stable E2E selectors

### Changed
- Browser opens in new window (`webbrowser.open_new`) instead of reusing existing tab
- Replaced argparse with click for CLI argument parsing
- E2E tests use `page.get_by_test_id()` instead of brittle text selectors

## [0.4.0] - 2026-04-12

### Added
- **Review summary** — general feedback not tied to a specific line (like GitHub PR review body)
- **Review modal** — "Finish review" button opens a modal with comment recap and summary textarea
- **Quick submit** — green button for immediate inline-comment-only submission (Ctrl+Shift+Enter)
- ReviewModal component with ARIA attributes (`role="dialog"`, `aria-modal`, `aria-labelledby`)
- Keyboard shortcut guard — Ctrl+Shift+Enter respects disabled button state
- E2E tests: modal submit, keyboard bypass prevention, Esc-close-and-preserve-body
- Self-review principles documented in AGENTS.md

### Changed
- Centralized Playwright page fixture with 5s timeout in conftest.py
- E2E tests refactored to use shared `page` fixture instead of manual browser management

## [0.3.1] - 2026-04-12

### Fixed
- Skill always upgrades CLI to latest on each run (no stale versions)
- Updated CONTRIBUTING.md with releasing steps and distribution channels

## [0.3.0] - 2026-04-12

### Added
- **Files mode** — review plain text files instead of git diffs (`claude-review --files plan.md`)
- `/review-ui plan` — review the current plan file before approving
- `ReviewMode` enum (diff, files) with mode-aware frontend rendering
- `TextFileService` — converts text files into reviewable content
- Flat file list sidebar for files mode (no tree structure, no diff badges)
- Simplified DiffView for non-diff modes (single line number column, no +/- prefixes)
- 20 new tests (unit, integration, E2E) for files mode

### Changed
- `create_app()` now requires explicit `mode` parameter (no silent default)
- `run()` accepts pre-loaded data instead of loading internally
- All `StrEnum` values use `auto()` instead of hardcoded strings
- Sidebar title derived from mode via lookup map (extensible for future modes)
- Diff-specific styling (row coloring, gutter classes) guarded by `isDiffMode`

## [0.2.0] - 2026-04-10

### Fixed
- Python 2 `except` syntax bug in git_repository.py (`except A, B:` → `except (A, B):`)
- Deprecated `asyncio.get_event_loop()` → `get_running_loop()`
- svelte-check warning in CommentBox (initialBody capture)

### Changed
- Replaced `xdg-open` subprocess with cross-platform `webbrowser.open()`
- Replaced closure-based DI with FastAPI `Depends()` pattern (presentation layer)
- Replaced fragile list holders with `ServerState` dataclass
- Made `diffStore.selectedFile` a `$derived` for proper reactivity

### Added
- structlog logging (silent by default, `--verbose` flag to enable)
- Pydantic field validators on `CommentInput` (positive lines, non-empty body, start ≤ end)
- 30s timeout on all git subprocess operations
- ESLint flat config for Svelte 5 + TypeScript (`eslint.config.js`)
- `diffStore.clear()` for test isolation
- Tests for heartbeat endpoint, state.result storage, and input validation (32 Python tests, 15 frontend tests)

### Removed
- Unused `pydantic-settings` dependency

## [0.1.0] - 2026-04-04

### Added
- Browser-based diff viewer with GitHub-style UI
- Syntax highlighting (Python, TypeScript, JS, CSS, HTML, Rust, Go, SQL, YAML, Markdown, Bash)
- Inline comments on single lines or drag-to-select ranges
- File tree sidebar with change stats (+/- per file)
- Comment navigation (prev/next)
- Light/dark theme toggle (auto-detects system preference)
- Auto-shutdown when browser tab is closed (heartbeat)
- Double-submit protection (409)
- Supports tracked, staged, and untracked files
- `/review-ui` slash command via `npx skills add`
- Claude Code plugin marketplace (`/plugin marketplace add vrppaul/claude-review`)
- CI: GitHub Actions (lint, Python tests, frontend tests, e2e, build verification)
- Pre-commit hooks: ruff, ty, bandit, conventional commits
- Auto-build frontend via hatch build hook (`uv build` builds both BE and FE)
- DDD-lite architecture: domain, services, repositories, presentation
- 29 Python tests (unit/integration/e2e with Playwright)
- 15 frontend tests (vitest)

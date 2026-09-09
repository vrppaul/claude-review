# Changelog

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

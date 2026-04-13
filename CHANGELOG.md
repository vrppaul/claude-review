# Changelog

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

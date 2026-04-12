# Changelog

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

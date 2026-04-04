# Changelog

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

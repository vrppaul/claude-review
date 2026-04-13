# Contributing

PRs welcome! Here's how to get started.

## Setup

```bash
# Clone
git clone https://github.com/vrppaul/claude-review.git
cd claude-review

# Python (requires Python 3.14+)
uv sync

# Frontend
cd frontend && pnpm install

# Install pre-commit hooks
uv run pre-commit install --hook-type commit-msg --hook-type pre-commit
```

## Development

```bash
# Run locally (diff mode)
uv run claude-review

# Run locally (files mode)
uv run claude-review --files some-file.md

# Run tests
uv run pytest                        # all Python tests
cd frontend && pnpm test             # frontend tests

# Lint & type check
uv run ruff check src/ tests/        # Python lint
uv run ruff format src/ tests/       # Python format
uv run ty check src/                 # Python type check
cd frontend && pnpm lint             # frontend lint
cd frontend && pnpm check            # frontend type check

# Build frontend
cd frontend && pnpm build            # outputs to src/claude_review/static/dist/
```

## Conventions

- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, etc.) — enforced by pre-commit hook
- **Python**: type hints on all signatures, async/await for I/O, Pydantic models (not dataclasses), structlog for logging, `StrEnum` with `auto()` for enums
- **Frontend**: Svelte 5 runes, TypeScript strict mode, no `any`
- **Tests**: test behavior, not implementation. TDD when possible.
- **Dependencies**: `uv add` for Python, `pnpm add` for JS — never specify versions
- **No meaningless defaults**: required parameters should be explicit, not silently defaulted

## Architecture

DDD-lite with clean layer separation:

```
presentation/  → FastAPI routes, Pydantic schemas, Depends() DI
services/      → orchestration (DiffService, TextFileService, ReviewService)
repositories/  → infrastructure (GitRepository)
domain/        → Pydantic models, protocols, enums
```

Dependencies flow inward: presentation → services → domain

The frontend uses a `ReviewMode` that flows from the backend API to control rendering:
- `diff` — two-column line numbers, add/delete styling, file tree sidebar
- `files` — single line numbers, no diff decoration, flat file list sidebar
- `transcript` — conversation messages as reviewable entries, markdown highlighting

See [AGENTS.md](AGENTS.md) for the full conventions reference.

## Releasing

1. Update version in **all three places** (keep in sync):
   - `pyproject.toml` — Python package version
   - `plugin/.claude-plugin/plugin.json` — plugin marketplace version
   - `CHANGELOG.md` — release notes
2. Update `plugin/commands/review-ui.md` if the skill's description or usage changed
3. Commit: `chore: release vX.Y.Z`
4. Push: `git push origin master --tags`
5. Tag: `git tag vX.Y.Z && git push origin vX.Y.Z`
6. Update local skill: `npx skills update review-ui -g -y`
7. Reinstall CLI locally: `uv tool install --upgrade --editable .`

Users install/upgrade the CLI via:
```bash
uv tool install --upgrade git+https://github.com/vrppaul/claude-review
```

Skills update via `npx skills update` — pulls latest from the repo.

## Distribution channels

- **CLI** — `uv tool install git+https://github.com/vrppaul/claude-review`
- **Skills** — `npx skills add vrppaul/claude-review -g -y` (cross-platform)
- **Plugin marketplace** — `/plugin marketplace add vrppaul/claude-review` (Claude Code)

All channels pull from this repo. Pushing to `master` updates skill definitions immediately. CLI users need to upgrade explicitly (handled by the skill's auto-upgrade check).

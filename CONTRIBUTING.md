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
uv run claude-review diff

# Run locally (files mode)
uv run claude-review files some-file.md

# Run tests
uv run pytest tests -n 4             # the Python tests; -m schema: the API's fuzzing
cd frontend && pnpm test             # frontend tests

# Lint & type check
uv run ruff check src/               # Python lint (the tests are formatted, never linted)
uv run ruff format src/ tests/       # Python format
uv run ty check src scripts          # Python type check
cd frontend && pnpm lint             # frontend lint
cd frontend && pnpm check            # frontend type check

# Build frontend
cd frontend && pnpm build            # outputs to src/claude_review/static/dist/
```

## Conventions

- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, etc.) — enforced by pre-commit hook
- **Python**: type hints on all signatures, async/await for I/O, Pydantic models (not dataclasses), structlog for logging, `StrEnum` with `auto()` for enums
- **Frontend**: Svelte 5 runes, TypeScript strict mode, no `any`
- **Tests**: only for a behavior someone can name — what the CLI prints, what a route answers, what the reader sees, where the keyboard lands — written before its code, at the cheapest level that sees it. Never for a look (a color, a size, a pixel): tokens, the linters and your own eyes in the browser hold it. Run the tests of the part you changed, and everything before a release. The full rules: `.claude/rules/tests.md`.
- **Dependencies**: `uv add` for Python, `pnpm add` for JS — never specify versions
- **No meaningless defaults**: required parameters should be explicit, not silently defaulted

## Architecture

DDD-lite with clean layer separation:

```
cli/           → the command line: launching a review, and the agent's commands
hosting/       → one review held open on this machine: its directories, port and server
presentation/  → FastAPI routes, wire models, Depends() DI
services/      → orchestration; services/review/ owns a review's state
repositories/  → infrastructure (GitRepository, the image and record stores, the clock)
domain/        → Pydantic models, the interfaces the services build on, enums
```

Each part builds only on those below it — cli → hosting → presentation →
services | repositories → domain — and the services and the repositories
never import each other. `uv run lint-imports` holds it. AGENTS.md says the
rest.

The frontend uses a `ReviewMode` that flows from the backend API to control rendering:
- `diff` — two-column line numbers, add/delete styling, file tree sidebar
- `files` — single line numbers, no diff decoration, flat file list sidebar
- `transcript` — conversation messages as reviewable entries, markdown highlighting

See [AGENTS.md](AGENTS.md) for the rules that bind all code, and the files under `.claude/rules/` it names for the rules of each area.

## Releasing

1. Update version in **all three places** (keep in sync):
   - `pyproject.toml` — Python package version
   - `plugin/.claude-plugin/plugin.json` — plugin marketplace version
   - `CHANGELOG.md` — release notes
2. If the release is worth telling a returning reader about, write its entry in `frontend/src/lib/guide/news.ts` under the same version — the review shows it once to whoever last saw an older release (optional; no entry, no card)
3. Update skill files if description or usage changed: `plugin/commands/review-ui.md` and `skills/review-ui/SKILL.md`
4. Update `README.md` features and `TODO.md` (remove completed items)
5. Commit: `chore: release vX.Y.Z`
6. Push + tag: `git push origin master && git tag vX.Y.Z && git push origin vX.Y.Z` — the tag triggers `release.yml`, which runs the full CI suite on the tagged commit, verifies the artifacts (`scripts/verify_artifacts.py`), and publishes to PyPI via trusted publishing. The workflow fails if the tag doesn't match the `pyproject.toml` version or if `plugin.json` is out of sync.
7. **Wait for the Release workflow to go green** — the version must be live on PyPI before skills point users at it (`uv tool install claude-review` fails until then).
8. Update local skill: `npx skills update review-ui -g -y`
9. Reinstall CLI locally: `uv tool install --upgrade --editable .`

Users install/upgrade the CLI via:
```bash
uv tool install --upgrade claude-review
```

Skills update via `npx skills update` — pulls latest from the repo.

## Distribution channels

- **CLI** — `uv tool install claude-review` (prebuilt wheel from [PyPI](https://pypi.org/project/claude-review/), no Node/pnpm needed)
- **Skills** — `npx skills add vrppaul/claude-review -g -y` (cross-platform)
- **Plugin marketplace** — `/plugin marketplace add vrppaul/claude-review` (Claude Code)

Skills and the plugin pull from this repo — pushing to `master` updates skill definitions immediately. The CLI is published to PyPI on tag push; CLI users upgrade explicitly (handled by the skill's auto-upgrade check).

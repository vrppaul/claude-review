# Claude Review

Browser-based code review tool for Claude Code. Shows git diffs in a GitHub-style UI, lets you write inline comments, sends formatted feedback back to Claude.

## Commands

```bash
uv sync                              # Install Python dependencies
uv run pytest                        # Run all Python tests
uv run pytest tests/unit/            # Unit tests only (pure logic, no I/O)
uv run pytest tests/integration/     # Integration tests (real git, real server)
uv run pytest tests/e2e/             # E2E tests (Playwright browser)
uv run ruff check src/               # Lint Python
uv run ruff format src/              # Format Python
uv run ty check src/                 # Type check Python
uv run claude-review                 # Run the tool
uv run claude-review --port 8080     # Run on specific port
cd frontend && pnpm install          # Install frontend dependencies
cd frontend && pnpm build            # Build frontend (outputs to src/claude_review/static/dist/)
cd frontend && pnpm test             # Run frontend tests
cd frontend && pnpm lint             # Lint frontend
cd frontend && pnpm check            # Type check frontend
```

All Python commands use `uv` — never use pip or manually activate a virtualenv. Use `uv init` to initialize, `uv add` to add dependencies (NEVER specify a version — let uv resolve), `uv run` to execute anything.

## Tech Stack

- **Python 3.14** — modern syntax (type parameter syntax, match, `str | None`)
- **uv** — project init, dependency management, running everything
- **hatchling** — build system
- **FastAPI + uvicorn** — async web server
- **Pydantic + pydantic-settings** — all models (domain, schemas, config)
- **structlog** — structured logging
- **ruff** — lint + format
- **pytest + pytest-asyncio** — Python tests
- **Svelte 5** — frontend (runes: `$state`, `$derived`, `$effect`)
- **Vite 6** — frontend build tool
- **TypeScript** — strict mode, no `any`
- **Tailwind CSS 4 + DaisyUI 5** — styling
- **pnpm** — JS package manager
- **Vitest + @testing-library/svelte** — frontend unit tests
- **Playwright** (Python, pytest-playwright) — E2E tests
- **ESLint + Prettier + svelte-check** — frontend code quality

## Architecture

DDD-lite with clean layer separation:

- **domain/** — Pydantic models (DiffFile, Comment, ReviewResult). No I/O, no framework imports.
- **services/** — orchestration (DiffService, ReviewService). Depends on domain + repository protocols.
- **repositories/** — infrastructure boundary (GitRepository). Protocol-based for testability.
- **presentation/** — FastAPI routes + Pydantic schemas. Thin layer calling services.

Dependencies flow inward: presentation → services → domain, repositories → domain

## Code Style

```python
import asyncio
from pathlib import Path
from typing import Protocol

import structlog

log = structlog.get_logger()


class GitRepositoryProtocol(Protocol):
    """Protocol for git operations."""

    async def get_diff(self, path: Path) -> str: ...


class GitRepository:
    """Git repository implementation using git CLI."""

    async def get_diff(self, path: Path) -> str:
        proc = await asyncio.create_subprocess_exec(
            "git", "diff", "HEAD",
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode()
```

## Conventions

- **TDD**: write tests BEFORE implementation. Tests encode functional requirements, not implementation details.
- **Test what the user cares about**: "diff shows all changed files", not "parse_hunk returns a list"
- **Modules**: `__init__.py` must be empty — no code, no re-exports, nothing
- **Error handling**: specific exceptions, not generic `Exception`
- **Python deps**: add via `uv add` (never specify version), never pip, never manually edit pyproject.toml deps
- **JS deps**: add via `pnpm add` / `pnpm add -D` (never specify version), never manually edit package.json deps
- **TODO/Changelog**: track in `TODO.md` / `CHANGELOG.md`
- **Logging**: DEBUG for timing/perf, INFO for operations, WARNING for recoverable issues, ERROR for failures
- **Type hints**: all function signatures, modern syntax (`str | None`, `list[X]`)
- **Async**: `async`/`await` for all I/O, no sync blocking calls
- **Enums**: use `StrEnum` for all string enumerations

## Boundaries

**Always:**
- Use `uv` for everything Python (`uv init`, `uv sync`, `uv run`, `uv add` without version)
- Use `pnpm` for everything JS (`pnpm add` / `pnpm add -D` without version, `pnpm run`)
- Use Pydantic models, not plain dataclasses
- Run tests (`uv run pytest`), linter (`uv run ruff check src/`), and type checker (`uv run ty check src/`) after changes
- Use structlog for logging, never print()
- Use type hints on all function signatures
- async/await for all I/O

**Ask first:**
- Adding new dependencies
- Architecture changes
- Changing domain models

**Never:**
- Use pip or activate venv manually
- Use plain dataclasses (always Pydantic BaseModel)
- Put any code in `__init__.py` files (no re-exports, no version, nothing)
- Use generic Exception for error handling
- Commit secrets or credentials

## Commit Messages

Conventional Commits: `type(scope): description`

Types: `feat fix docs style refactor perf test build ci chore`

## Documentation

- `README.md` — project overview, usage, installation
- `CHANGELOG.md` — what changed and when
- `TODO.md` — planned work

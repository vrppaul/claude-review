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
```

## Development

```bash
# Run locally
uv run claude-review

# Run tests
uv run pytest                        # all Python tests
cd frontend && pnpm test             # frontend tests

# Lint & type check
uv run ruff check src/               # Python lint
uv run ruff format src/              # Python format
uv run ty check src/                 # Python type check
cd frontend && pnpm lint             # frontend lint
cd frontend && pnpm check            # frontend type check

# Build frontend
cd frontend && pnpm build            # outputs to src/claude_review/static/dist/
```

## Conventions

- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, etc.)
- **Python**: type hints on all signatures, async/await for I/O, Pydantic models (not dataclasses), structlog for logging
- **Frontend**: Svelte 5 runes, TypeScript strict mode, no `any`
- **Tests**: test behavior, not implementation. TDD when possible.
- **Dependencies**: `uv add` for Python, `pnpm add` for JS — never specify versions

## Architecture

DDD-lite with clean layer separation:

```
presentation/  → FastAPI routes, Pydantic schemas, Depends() DI
services/      → orchestration (DiffService, ReviewService)
repositories/  → infrastructure (GitRepository)
domain/        → Pydantic models, protocols, exceptions
```

Dependencies flow inward: presentation → services → domain

See [AGENTS.md](AGENTS.md) for the full conventions reference.

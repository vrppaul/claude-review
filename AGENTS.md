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
uv run claude-review                 # Run the tool (diff mode)
uv run claude-review --files f.md    # Run the tool (files mode)
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
- **Pydantic** — all models (domain, schemas)
- **structlog** — structured logging
- **ruff** — lint + format
- **pytest + pytest-asyncio** — Python tests
- **Svelte 5** — frontend (runes: `$state`, `$derived`, `$effect`)
- **Vite 8** — frontend build tool
- **TypeScript** — strict mode, no `any`
- **Tailwind CSS 4 + DaisyUI 5** — styling
- **pnpm** — JS package manager
- **Vitest + @testing-library/svelte** — frontend unit tests
- **Playwright** (Python, pytest-playwright) — E2E tests
- **ESLint + Prettier + svelte-check** — frontend code quality

## Architecture

DDD-lite with clean layer separation:

- **domain/** — Pydantic models (DiffFile, Comment, ReviewResult). No I/O, no framework imports.
- **services/** — orchestration (DiffService, TextFileService, ReviewService). Depends on domain + repository protocols.
- **repositories/** — infrastructure boundary (GitRepository). Protocol-based for testability.
- **presentation/** — FastAPI routes + Pydantic schemas + `Depends()` DI. Routes declare dependencies explicitly.

Dependencies flow inward: presentation → services → domain, repositories → domain

## Code Style

```python
# Domain — pure models, no I/O
class FileStatus(StrEnum):
    MODIFIED = auto()
    ADDED = auto()

# Protocols — interfaces for infrastructure
class GitRepositoryProtocol(Protocol):
    async def get_raw_diff(self, path: Path) -> str: ...

# Presentation — FastAPI routes with Depends() DI
@router.post("/submit")
async def submit_review(
    request: SubmitRequest,
    state: ServerState = Depends(get_state),
    review_service: ReviewService = Depends(get_review_service),
) -> SubmitResponse:
    ...
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
- **Enums**: use `StrEnum` with `auto()` for all string enumerations

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

## Self-Review

Before presenting work, review every changed file against these principles:

**Clean and readable** — each function does one thing. No god methods. Decompose like existing services do (e.g. `DiffService` has `_parse_diff`, `_parse_file_chunk`, `_extract_path`, `_detect_status`, `_parse_hunks`, `_build_hunk`).

**Well documented / self-documenting** — names explain intent. Non-obvious patterns get a one-line comment (e.g. `# Only close when clicking the backdrop itself, not the modal content`). Module docstrings explain *why*, not just *what*.

**Functional tests** — tests verify user-facing behavior, not internal data structures. Test names read like requirements: "file content is preserved line by line", not "returns list of DiffLine with type CONTEXT". Compare `tests/integration/test_diff_service.py` for the standard.

**Modular** — components and services are independently testable. Dependencies are explicit (FastAPI `Depends()`, constructor injection). No hidden coupling between layers.

**No meaningless defaults** — required parameters must be explicit. If a caller must always provide a value, don't give it a default that silently hides bugs. Optional parameters (like `body: str | None = None`) are fine when the absence is a valid state.

**Extensible for future modes** — new review modes (transcript, etc.) should work by adding code, not modifying existing conditionals. Use `isDiffMode` checks (opt-in to diff-specific behavior) rather than `!isFilesMode` checks (which break when a third mode is added). Use lookup maps for mode-dependent values (see `sidebarTitle` in `FileList.svelte`).

## Commit Messages

Conventional Commits: `type(scope): description`

Types: `feat fix docs style refactor perf test build ci chore`

## Documentation

- `README.md` — project overview, usage, installation
- `CHANGELOG.md` — what changed and when
- `TODO.md` — planned work
- `CONTRIBUTING.md` — dev setup, conventions for contributors
- `SECURITY.md` — vulnerability reporting

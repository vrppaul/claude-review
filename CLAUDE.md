# Claude Review

See [AGENTS.md](AGENTS.md) for commands, tech stack, conventions, and boundaries.

## Key Architecture

cli → FastAPI server → browser UI → submit → formatted output

DDD-lite: domain/ (Pydantic models) → services/ (orchestration) → repositories/ (git) → presentation/ (FastAPI routes)

## Implementation Discipline

- **Small chunks.** One logical piece at a time. Present for review. Never blast through a multi-phase plan.
- **Understand before writing.** No code without full understanding of what exists and where the change belongs.
- **Self-review before presenting.** Correct layer? Redundant work? Non-obvious logic commented? Every line necessary?

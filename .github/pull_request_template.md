## What changes

<!-- What a user can now see or do, and why. For a refactor, what is simpler now. -->

## How it was checked

- [ ] `uv run pre-commit run --all-files` passes
- [ ] The tests of the part changed pass: `uv run pytest tests -n 4`, `cd frontend && pnpm test`, and `uv run pytest tests/e2e -n 4` for a change to the page
- [ ] A change to the page was looked at in a browser (`uv run claude-review diff`)
- [ ] A change a user would notice has its line in `CHANGELOG.md` under `[Unreleased]`

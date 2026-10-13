# Claude Review

A code review in the browser for Claude Code: it shows a git diff, files or a transcript, takes comments on their lines, and sends them back to the agent.

## Commands

```bash
uv sync                              # Python dependencies
uv run pytest                        # every Python test: tests/unit, tests/integration, tests/e2e
uv run pre-commit run --all-files    # every gate a commit runs, over every file (CI's lint job runs this)
uv run claude-review diff            # run the tool; `files` and `transcript` are its other modes
cd frontend && pnpm install          # the page's dependencies
cd frontend && pnpm build            # build the page into the package
cd frontend && pnpm test             # the page's tests
cd frontend && pnpm lint             # eslint and stylelint
cd frontend && pnpm check            # svelte-check
cd frontend && pnpm format           # Prettier; the hook only checks
```

- The gates are one list, `.pre-commit-config.yaml`, each with its command. A hook that cannot run fails: leave one out only on purpose, by naming it in `SKIP`.
- Python runs through `uv`, the page through `pnpm`. Add a dependency with `uv add`, `pnpm add` or `pnpm add -D` and no version: never pip, an activated virtualenv, or a hand edit of a dependency list.

## How we work

- **Small chunks.** One logical piece at a time, presented for review. Never a run through a plan of several phases.
- **Understand before writing.** No code without full understanding of what exists and where the change belongs.
- **Tests first.** Write the test before the code: it states a requirement, not how the code meets it.
- **Review before presenting.** Read every changed file: the right layer? redundant work? the non-obvious commented? every line needed?
- After a change, run the tests and every gate.
- **Ask first** before adding a dependency, changing the architecture, or changing a domain model.
- Never commit secrets or credentials.
- A commit follows Conventional Commits, `type(scope): description`; a hook holds the types.
- Planned work is tracked in `TODO.md`, where an item done is removed, not ticked off; what changed, in `CHANGELOG.md`.

## Layers

- `cli` → `hosting` → `presentation` → `services` | `repositories` → `domain`, the parts of `src/claude_review/`: each builds only on those after it, and the services and the repositories never import each other.
- The domain, the services and the repositories import no web server and no command-line framework; an agent's command, with all it imports, no web server and no web framework.
- `uv run lint-imports` refuses an import against these; `pyproject.toml` holds the contracts and their reasons.

## Rules for all code

- A function does one thing, as `src/claude_review/services/unified_diff.py` is split (`_path`, `_status`, `_hunks`, `_hunk`); no method does everything.
- A name says what it holds. What is not obvious gets a one-line comment. A module's docstring says why, not only what.
- Dependencies are explicit — FastAPI's `Depends()`, a constructor's parameters — so a service or a component is tested by itself, and nothing couples two layers out of sight.
- A parameter every caller must give has no default, which would hide a missing value. One whose absence is a valid state may have one.
- A new review mode is added code, not a changed conditional: opt in to a mode (`isDiffMode`), never out of one (`!isFilesMode`), and look up what depends on the mode in a table (`COUNTED_AS`).

## Only better, and who says so

Every change leaves the repository better than it found it — cleaner, more readable, more modular, its
architecture more fitting — in every part it touches, not on balance. The rule being written down has not
been enough: whoever writes a change can talk themselves into trading it for convenience. So three things
hold a change to it, and none is its author's own judgement:

- **The verdict is somebody else's.** A chunk of work is not done, and its author says nothing of it being
  better, until an independent reviewer has measured its whole diff against this rule, given to it word for
  word, and listed every place that got worse. That review is part of the chunk, never a favour asked for it.
- **A regression found becomes a gate.** Whatever a review catches is turned into a rule a tool enforces —
  `scripts/check_code_rules.py`, a linter's rule, a test over the package — so that kind of mistake cannot be
  made again whatever its author thinks. A form a type checker refused is never answered with a form it
  cannot see.
- **What its author can name as worse is not committed.** Anything that would be listed under "did not get
  better" is put right before the commit, or the work stops there and the owner is asked: it is never a note
  in the report afterwards.

## Rules by area

Before you change or review code in an area, read its file whole. Claude Code loads it only when it opens a file of the area, and nothing else loads it: a brief to another agent names the files.

- `.claude/rules/server.md` — anything under `src/` or `scripts/`: Python, the package's parts, models, errors, time, the command line.
- `.claude/rules/wire.md` — a wire model, a route, the API's schema, the page's generated types and its requests.
- `.claude/rules/page.md` — anything under `frontend/`: types, state, parts, styling, panes and keys, moving the reader.
- `.claude/rules/tests.md` — any test, under `tests/` or `frontend/tests/`.
- `CONTRIBUTING.md`, under Releasing — a release.

## Changing these files

- A new rule is a new bullet a reviewer can check, in the file of its area: never a sentence added to a paragraph.
- How a thing is built is said in its module's docstring, not here.
- What a tool can hold is a gate, not a rule: write the gate.
- `CLAUDE.md` is a symlink to this file, for Claude Code to read it by: edit this one.

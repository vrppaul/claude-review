# Claude Review

A code review in the browser for Claude Code: a git diff, files or a transcript, commented line by line and sent back to the agent.

## Commands

```bash
uv sync                              # Python dependencies
uv run pytest tests -n 4             # the Python tests; -m schema: the API's fuzzing
uv run pre-commit run --all-files    # every gate a commit runs, over every file
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
- **Tests hold behaviour.** A behaviour someone can name gets a test first, at the cheapest level; a look, a refactor or a declaration gets none.
- **Review before presenting.** Read every changed file: the right layer? redundant work? the non-obvious commented? every line needed?
- **Test runs follow the change.** Which tests run when: `.claude/rules/tests.md`.
- **Speed is measured.** Say with each piece how long it took and what its slowest step was.
- **Ask first** before adding a dependency, changing the architecture, or changing a domain model.
- Never commit secrets or credentials.
- A commit follows Conventional Commits, `type(scope): description`.
- Every sentence of a commit message is a claim: look before you write it, and read a count off a command's output.
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
- Shared code comes with its second user, not before; once there are two, it is written once.

## Only better

Every change leaves the repository better than it found it: cleaner, easier to read, more modular, its architecture more fitting. In every part it touches, not on balance. A change that only works is not done.

- **Construction first.** Before code, settle who owns each state and for how long, which layer it lives in, and the contract. Build nothing nobody asked for.
- **Simplest first.** Build the simplest thing that works. A new state, listener, table, gate or module says why nothing simpler does; a reviewer's fix is a proposal. Unsure how? Ask the owner, never build it complicated.
- **Root cause first.** Before a fix, say why the fault can happen and change that construction. A flag, guard or filter hiding a wrong value is a symptom fix: it needs a reason.
- **Show it with facts, not adjectives.** Say what a reader can check: what was written several times and is now written once, which state has one owner now, which rule a tool now holds. Say as plainly what did not get better.
- **The verdict is somebody else's.** A chunk is done when an independent reviewer has measured its whole diff against this rule and listed every place that got worse. Its author never calls it better.
- **A review steps back.** Ask why each part the change lives in exists at all, from more than one side, against how the framework's docs and template do it. One with no reason that holds is a finding, however old.
- **A regression found becomes a gate.** What a review catches turns into a rule a tool enforces at the commit, not a test. A form a checker refused is never answered with a form it cannot see.
- **What you can name as worse is not committed.** Fix it, or stop and ask.

## Rules by area

Before you change or review code in an area, read its file whole; a brief to another agent names the files.

- `.claude/rules/server.md` — anything under `src/`: Python, the package's parts, models, errors, time, the command line.
- `.claude/rules/wire.md` — a wire model, a route, the API's schema, the page's generated types and its requests.
- `.claude/rules/page.md` — anything under `frontend/`: types, state, parts, styling, panes and keys, moving the reader.
- `.claude/rules/design.md`, `.claude/rules/design-behaviour.md`, `.claude/rules/design-process.md` — how the page looks and answers the reader, and how a design is made.
- `.claude/rules/tests.md` — any test, under `tests/` or `frontend/tests/`.
- `.claude/rules/scripts.md` — anything under `scripts/`: what a script is, how it runs a command, how it is tested.
- `.claude/rules/instructions.md` — this file and the rules of each area.
- `CONTRIBUTING.md`, under Releasing — a release.

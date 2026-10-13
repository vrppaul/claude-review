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
- **Test runs have a budget.** While you iterate, run only the tests of the code in hand; pre-commit runs the gates at the commit. The whole suite runs once per chunk, at its end.
- **Speed is measured.** Say with each piece how long it took and what its slowest step was. A tool we write does its whole job in one process start; one that takes over half a minute is made fast or not used.
- **Ask first** before adding a dependency, changing the architecture, or changing a domain model.
- Never commit secrets or credentials.
- A commit follows Conventional Commits, `type(scope): description`; a hook holds the types.
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
- **Show it with facts, not adjectives.** Say what a reader can check: what was written several times and is now written once, which state has one owner now, which rule a tool now holds. Say as plainly what did not get better.
- **The verdict is somebody else's.** A chunk is done when an independent reviewer has measured its whole diff against this rule and listed every place that got worse. Its author never calls it better.
- **A regression found becomes a gate.** What a review catches turns into a rule a tool enforces. A form a checker refused is never answered with a form it cannot see.
- **What you can name as worse is not committed.** Fix it, or stop and ask.

## Rules by area

Before you change or review code in an area, read its file whole. Claude Code loads it only when it opens a file of the area, and nothing else loads it: a brief to another agent names the files.

- `.claude/rules/server.md` — anything under `src/`: Python, the package's parts, models, errors, time, the command line.
- `.claude/rules/wire.md` — a wire model, a route, the API's schema, the page's generated types and its requests.
- `.claude/rules/page.md` — anything under `frontend/`: types, state, parts, styling, panes and keys, moving the reader.
- `.claude/rules/tests.md` — any test, under `tests/` or `frontend/tests/`.
- `CONTRIBUTING.md`, under Releasing — a release.

## Changing these files

- A new rule is a new bullet a reviewer can check, in the file of its area: never a sentence added to a paragraph.
- How a thing is built is said in its module's docstring, not here.
- What a tool can hold is a gate, not a rule: write the gate.
- `CLAUDE.md` is a symlink to this file, for Claude Code to read it by: edit this one.
- `scripts/check_instruction_files.py` holds each of these files to its size, and every path they name to being there.

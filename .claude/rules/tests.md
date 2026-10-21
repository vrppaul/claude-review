---
paths:
  - "tests/**"
  - "frontend/tests/**"
---

# Tests

## When a test is written

- A test holds a behaviour someone can name: it does one thing — a press, a key, a command, a request, a call — and checks what came of it.
- What came of it: the words shown or the sound heard, what holds the keyboard, what is in view, what reached the server, what the CLI printed or refused, what a route answered or pushed, what a story rule or the domain decided.
- Its name states that behaviour: `tests/integration/test_diff_reading.py` is the standard.
- First find the test that already holds the behaviour and extend it. A new test only where none does.
- It is written before its code and seen failing. A refactor gets no new test: the old ones pass unchanged.
- A test rewritten is seen failing too: with the line of code it holds broken, then restored.
- Never how it looks: no colour, size, weight, face, corner, room, pixel, opacity or position, measured or read from a style. Tokens, the gates and a reviewer's eye hold a look.
- A width the reader sets, dragging a column or with its keys, is what they did, not a look: a test may hold it.
- How far an area has scrolled is what a scroll or a key did: a test may compare it, never where a box stands.
- No test for a declaration (a field's bound, a click option, a status code), a library's own behaviour, internals (listeners, timers, an inner structure) or a test helper.
- "No test holds X" is no finding and no TODO item unless X is a behaviour someone can name.
- A rule about how code is written is a gate in pre-commit, never a test.
- A test deleted leaves no debt: nothing is written in its place, neither a test nor a gate. A gate of our own code, a plugin or a script, is built only on the owner's word.

## At which level

- One level, the cheapest that sees the behaviour. Logic: `tests/unit/`, pure, no I/O, or a vitest test of the review's model.
- A route: once per call site in `tests/integration/`, never its rule's cases again.
- A real server: sockets, backpressure and lifetime alone. A subprocess: exit codes, stderr and signals alone. Real git: what git decides.
- `tests/e2e/` holds what only a real browser does: its own focus (a dialog, Tab, a disabled control), scrolling, CSP, mermaid, one round trip per agent command.
- Focus the page moves, what a key does and what is drawn are vitest.
- No browser test runs once per theme; once per width only where its claim is about that width.
- `tests/scripts/` runs a gate as it is run. A script that only serves or looks has a smoke test at most.

## How a test is written

- A test and its helpers hold no branch: no `if`, no conditional expression, no `or`, no filter in a comprehension. A helper that depends on a kind is a lookup table.
- Cases of one rule are one test that names every case that fails. A property test (hypothesis, fast-check) replaces the example tests of its rule, one example kept at most.
- Data with a shape is a typed model, never a raw `dict` or `Mapping`, in tests too.
- A request's or an answer's JSON is written out by hand only where a test speaks as the browser or the agent and its neighbours already do.
- The tests are held to formatting, `ruff format` and Prettier: no linter, type checker or spelling check reads them. vulture and knip read them for what of the package and the page they use.
- Two hooks read them for a look alone, each naming the reads it refuses (`.pre-commit-config.yaml`); `tests/e2e/placing.py` is the one setup let alone.
- A test acts on an element by its `data-testid`, and never asserts one. `getByText` and `text=` only assert words the user sees. Never a CSS class selector.

## The browser

- A test that drives the browser opens the suite's own `page` fixture (`tests/e2e/conftest.py`), on Playwright's async API: each process of a run launches Chromium once.
- Every test under `tests/e2e/` runs in the event loop the browser was launched in, so an async fixture one of them asks for is declared with `in_the_browsers_loop` (`tests/e2e/browsers_loop.py`).
- No pytest plugin of Playwright's is installed, so `--headed` and `--browser` are refused, not taken and ignored.

## Runs

- Iterating: the tests of the code in hand. A commit runs the gates alone.
- At a chunk's end each part changed runs once, by whoever commits; a reviewer reads that run and does not repeat it.
- The page: vitest, and `tests/e2e` where the change touches what it holds.
- The server: `tests/unit` and `tests/integration`, and `tests/e2e` and the schema's fuzzing (`-m schema`) where a route or a schema changes. `scripts/`: that script's tests.
- A release, or a merge to master, runs everything, `-m schema` with it.
- A review's findings about tests are two: a test to delete (a look, a twin, internals, one that cannot fail) and a behaviour no test holds.

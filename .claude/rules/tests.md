---
paths:
  - "tests/**"
  - "frontend/tests/**"
---

# Tests

## What a test states

- A test states a requirement, not how the code meets it: what the user cares about ("diff shows all changed files"), never an internal data structure ("parse_hunk returns a list").
- Its name reads as the requirement: "file content is preserved line by line", not "returns list of DiffLine with type CONTEXT". `tests/integration/test_diff_reading.py` is the standard.
- `tests/unit/` is pure logic with no I/O, `tests/integration/` real git and a real server, `tests/e2e/` the page in the suite's browser, `tests/scripts/` the scripts under `scripts/`, run as they are run.
- A property that must hold whatever the input is a hypothesis test, and on the page a fast-check one.

## How a test is written

- A test and its helpers hold no branch: no `if`, no conditional expression, no `or`, no filter in a comprehension. A test that chooses what to expect is two tests in one body, and a branch can hide a case that never runs.
- One case to a property, over inputs made by construction to be that case. A helper that depends on a kind is a lookup table.
- A test seen failing before its code exists is the proof that it holds that code. Break a line on purpose only where no such run was seen, and then all such breaks in one run: `scripts/break_lines.py`, for the page.
- Data with a shape is a typed model, never a raw `dict` or `Mapping`, in tests too: a raw one hides the shape and lets a misspelt key through.
- Wire JSON is written out by hand only where a test speaks as the browser or the agent and its neighbours already do.
- The tests are held to formatting alone, `ruff format` and Prettier: no linter, type checker or spelling check reads them. vulture and knip read them for what of the package and the page they use.

## Finding elements

- A test acts on an element (click, type, check disabled) by its `data-testid`.
- `getByText` and `text=` only assert words the user sees.
- Never a CSS class selector in a test.

## The browser

- A test that drives the browser itself opens the suite's own `page` fixture (`tests/e2e/conftest.py`), on Playwright's async API: each process of a run launches Chromium once.
- Every test under `tests/e2e/` runs in the event loop the browser was launched in, so an async fixture one of them asks for is declared with `in_the_browsers_loop` (`tests/e2e/browsers_loop.py`).
- No pytest plugin of Playwright's is installed, so `--headed` and `--browser` are refused, not taken and ignored.
- Where the keyboard lands, what a dialog holds and what the layout does are tested in the browser: jsdom cannot stand in for one. What each key does is tested in vitest.

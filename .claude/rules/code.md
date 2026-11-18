---
paths:
  - "src/**"
  - "scripts/**"
  - "hatch_build.py"
  - "frontend/src/**"
---

# Any code

What holds in Python and on the page alike. Each has its own besides: `.claude/rules/server.md`, `.claude/rules/scripts.md`, `.claude/rules/page.md`. What of this a test keeps: `.claude/rules/tests.md`.

## Functions and names

- A function does one thing, as `src/claude_review/services/unified_diff.py` is split (`_path`, `_status`, `_hunks`, `_hunk`); no method does everything.
- A name says what it holds, in full words, a coordinate or an index too: `first_row`, `offsetY`, never `r`, `t0`, `idx`, `x`.
- No function inside another: a helper is a function of its module, with a name and parameters. A short lambda handed to a call is none.
- No function only passes its call on, fixed arguments or none, unless it names a notion its call lacks or hides real work; shorter to write is no reason.
- No alias and no shim for what something was called: rename a thing and fix every user.

## Values and state

- No literal with a meaning in an expression: a number, a colour, a timing, a size, a string key is a named constant or data; what its name cannot say, a comment does.
- A member of a closed set the type checker holds, compared in place (`review.mode === 'diff'`), is no such literal.
- No tuple where a type belongs: data with a shape is a named type.
- No state a module keeps and changes: what is shared is built in one place and handed to who needs it.
- Nothing derived is worked out again in a loop that runs often: it is kept where its source changes.
- A parameter every caller must give has no default, which would hide a missing value. One whose absence is a valid state may have one.
- Dependencies are explicit — FastAPI's `Depends()`, a constructor's parameters — so a service or a component is tested by itself, and nothing couples two layers out of sight.

## Growing

- A new review mode is added code, not a changed conditional: opt in to a mode (`isDiffMode`), never out of one (`!isFilesMode`), and look up what depends on the mode in a table (`COUNTED_AS`).
- Shared code comes with its second user, not before; once there are two, it is written once.
- Code nearby that breaks these is no model: write it down in `TODO.md` and tell the owner, never copy it.

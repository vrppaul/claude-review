---
paths:
  - "src/**"
  - "scripts/**"
---

# The server and the command line

How a module is built is said in its docstring. What crosses the wire has its own rules, `.claude/rules/wire.md`.

## Python

- Write Python 3.14: type parameter syntax, `match`, `str | None`, `list[X]`.
- Every function signature carries type hints.
- All I/O is `async` and awaited: no blocking call.
- A model is a Pydantic model, never a plain dataclass.
- A string enumeration is a `StrEnum` with `auto()`.
- Every `**/__init__.py` is empty: no code, no re-exports, no version.
- Raise and catch a specific exception, never `Exception`.
- Log through structlog, never `print()`: DEBUG for timing, INFO for operations, WARNING for what was recovered from, ERROR for failures.

## The parts

- The domain does no I/O.
- A service is a class where there is a dependency or state to hold, a function where there is not.
- A service builds on the domain and the interfaces it holds (`src/claude_review/domain/interfaces.py`), never on what implements them; a test puts a fake in an implementation's place.
- `src/claude_review/services/review/` is the one owner of a review's state. It tells the pages what happened as `PageEvent`s, through the `PageChannel` interface.
- The domain holds an anchor's place, never words for it: `src/claude_review/services/place_words.py` writes the words.
- A review is put together in one place, `host_review`, for the command line and the tests alike.
- Hosting prints nothing: what whoever started the review must hear goes through a `ReviewAnnouncer`.

## Interfaces and models

- An interface is an abstract class (`ABC`), never a `typing.Protocol`: every implementation inherits it, so the type says what the code does.
- Every member of an interface is `@abstractmethod`. Every method an implementation writes is marked `@override`, so ty holds it to the interface where it is written.
- A model made from another is made by a method of the model (`DiffFile.showing`, `LineAnchor.lost`, `Step.told`), which calls its constructor with every field written out: ty then holds the names, the types and the fields it must have.
- Each such method adds its row to `tests/unit/test_models_made_from_models.py`: a field with a default left out is what ty cannot see.
- No model is taken apart into its fields by name: `scripts/check_code_rules.py` refuses `model_copy`, `model_construct`, `model_dump`, `__dict__`, `vars` and `copy.replace`.
- What that check cannot see by a name, a model handed to `dict(…)` or walked field by field, is forbidden all the same.
- A model leaves for the wire as JSON (`model_dump_json`), never as a mapping.

## Errors and time

- Whatever the review refuses is a `ReviewError` of one kind, in `src/claude_review/domain/exceptions.py`: `NotFoundError`, `InvalidRequestError`, `RefusedError` (`TooLargeError` is one), `ConflictError`.
- A refusal says one thing wrong. What is sent whole and may be wrong in many places, a document, is refused with every fault at once, each at its field: a `FieldsRefusedError` of `FieldFault`s.
- Every moment the review says is `EpochMillis`, read from the `Clock` the review is built with (`FixedClock` in tests): never `time.time()` in a route or a service.
- Nothing waits on the clock: a grace period is a timeout on an event, not a comparison of moments.

## The command line

- A click command takes its options keyword-only (`*`): click hands them over by name, and nothing calls a command with a bare `True`.
- Every value an agent's command takes is checked against the review's own rule as it is parsed (`src/claude_review/cli/parameters.py`), so a mistake is a usage error that names the option.
- An agent's command never loads the server or its framework: `src/claude_review/cli/main.py` loads each command only when it is run.
- Whatever the reader or the repository wrote is printed through `terminal_text`, so a terminal's own controls in it are shown, never obeyed.
- A text an agent's command takes may be `-`, read from stdin: the way to hand over anything the shell would rewrite.

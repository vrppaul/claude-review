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
uv run ty check src/                 # Type check Python (a warning fails it too)
uv run lint-imports                  # The package's parts import in one direction only (pyproject.toml's contract)
uv run vulture                       # Code nothing calls (what frameworks call is listed in pyproject.toml)
uv run deptry src                    # Every import declared as a dependency, every dependency imported
uv run python scripts/check_code_rules.py src scripts  # No function inside another, no name too short, no model taken apart by its fields' names
uv run typos                         # Spelling, in code and prose alike
uv run pre-commit run --all-files    # Every gate a commit runs, over every file (CI's lint job runs this)
uv run claude-review diff                    # Run the tool (diff mode)
uv run claude-review diff --base HEAD~3      # Diff since a specific commit
uv run claude-review files f.md              # Run the tool (files mode)
uv run claude-review transcript c.jsonl      # Run the tool (transcript mode)
uv run claude-review diff --port 8080        # Run on specific port
cd frontend && pnpm install          # Install frontend dependencies
cd frontend && pnpm build            # Build frontend (outputs to src/claude_review/static/dist/)
cd frontend && pnpm test             # Run frontend tests
cd frontend && pnpm lint             # Lint frontend
cd frontend && pnpm format           # Format frontend (src, tests, configs; .svelte too)
cd frontend && pnpm format:check     # Fail on anything Prettier would change (the pre-commit hook runs this)
cd frontend && pnpm knip             # Files, exports and dependencies nothing uses (`knip --production`: what only tests use)
cd frontend && pnpm check            # Type check frontend
cd frontend && pnpm api:types        # Regenerate src/lib/types/generated/ from the server's schemas
cd frontend && pnpm api:check        # Fail if the generated types no longer match the server (CI runs this)
```

All Python commands use `uv` — never use pip or manually activate a virtualenv. Use `uv init` to initialize, `uv add` to add dependencies (NEVER specify a version — let uv resolve), `uv run` to execute anything.

## Tech Stack

- **Python 3.14** — modern syntax (type parameter syntax, match, `str | None`)
- **uv** — project init, dependency management, running everything
- **hatchling** — build system
- **FastAPI + uvicorn** — async web server
- **Pydantic** — all models (domain, wire)
- **structlog** — structured logging
- **ruff** — lint + format
- **pytest + pytest-asyncio** — Python tests; **hypothesis** for properties that must hold whatever the input
- **Svelte 5** — frontend (runes: `$state`, `$derived`, `$effect`)
- **Vite 8** — frontend build tool
- **TypeScript** — strict mode, no `any`
- **Tailwind CSS 4 + DaisyUI 5** — styling
- **pnpm** — JS package manager
- **Vitest + @testing-library/svelte** — frontend unit tests; **fast-check** for properties
- **Playwright** (Python, its async API) — E2E tests; the page each test opens is the suite's own fixture (`tests/e2e/conftest.py`), and no pytest plugin of Playwright's is installed, so `--headed` and `--browser` are refused rather than taken and ignored
- **ESLint + Prettier + svelte-check** — frontend code quality

## Architecture

DDD-lite with clean layer separation:

- **domain/** — Pydantic models (DiffFile, Thread, ReviewResult). No I/O, no framework imports.
- **services/** — orchestration: a class where there is a dependency or state to hold, a function where there is not (`read_diff` over the pure `unified_diff` parser, `read_text_files` and `read_transcript` over `whole_file`, `RoundFormatter`, which writes a round the way each kind of review leads into its threads, and `place_words`, which names an anchor's place in plain words or in Markdown — the domain holds the place, never words for it — and reads a run of lines back from the words for one; a story the agent tells of a change is checked whole, every fault at once (`story_checks`; `story_lines_told` keeps which step first told each line of a file, so a step is found to tell one twice without being held against every other), placed on the change by one rule for which rows a step's lines are (`story_slices`, a `PlacedFile` per file), and told, each step with the piece it shows and what no step tells beside it (`story_telling`)). Depends on the domain and its interfaces (`domain/interfaces.py`). `services/review/` is the one owner of a review's state: `Review` (`review.py`) composed of its parts — `ReviewLifetime`, `BrowserPresence` (pages open, no polling), `Answerer`, `AgentInbox` (what the agent waits on), `RoundTracker`, `Conversation`, `ReaderThreads`, `ReviewStory` (the story told of the change, kept with the round it was told in and the take it was told of), and a `ContentSource` (`RepositorySource` or `FixedSource`) holding the `ReviewContent` of the current take, numbered as each is made, and its `ReviewVersions`. It tells pages what happened as domain `PageEvent`s through the `PageChannel` interface.
- **repositories/** — infrastructure boundary (`GitRepository`, the image and record stores, the system clock), each implementing an interface the domain holds, so the services build on the interface and a test puts a fake in its place.
- **presentation/** — FastAPI routes + the wire models (`wire/`) + `Depends()` DI. Every model that crosses the wire is a `WireModel` of its own in `wire/` (base, content, threads, agent, pushes, records, story), built from the domain model of the same shape with `.of()`; the domain never carries wire settings. A wire model may implement an interface the domain holds, where a service asks for what the request carries: a change to a reader's record is a `RecordChange`, which says for itself what it makes of the record. Routes (`routes/`: page, agent, reader records, session socket, mounted by `include_api`) are thin: they read the wire, call one method of the `Review` they get from `get_review`, and write the answer. `BrowserBroadcast` is the `PageChannel`: it writes each `PageEvent` as its `ServerPush` (`wire/pushes.py`) once — `event_pushes.py` is the one place an event becomes its push — and queues it for every open page; `version_words.py` names the bases the page asks by; `api_schema.py` writes the OpenAPI the browser's types come from. `LocalOriginOnly` lets in what `admits` (`origin_guard.py`) admits, and nothing else: that function is the guard's whole rule, from the request's Host, Origin and Sec-Fetch-Site. The app opens the review (`Review.open`) in its lifespan, so whatever serves it starts it right.
- **hosting/** — holds one review open on this machine: its directories, its port, its uvicorn server, and the review's parts that run until its `ReviewLifetime` ends. `host_review` (`hosted_review.py`) is where a review is put together — on the repository it is given, with its images, its broadcast and its app — for the command line and the tests alike. `serve_review` (`serving.py`) serves a hosted review on the socket it is handed until it ends; `hold_open` is the command line's way in, giving the review its workspace, git as its repository (writing trees into that workspace) and its port. It prints nothing: what whoever started the review must hear goes through a `ReviewAnnouncer`.
- **Layers**: `cli` → `hosting` → `presentation` → `services` | `repositories` → `domain`, each building only on those after it; the services and the repositories sit side by side and never import each other. The domain, the services and the repositories import no web server and no command-line framework (FastAPI, Starlette, uvicorn, wsproto, click): those belong to the parts that serve and start a review. The agent's commands, and everything they import — the wire models they share with the routes among it — import no web server and no web framework: a command must not load what serves the review to send it a request. `lint-imports` refuses an import against any of these rules.
- **cli/** — the command line. The launch commands (`diff`, `files`, `transcript`) read what is reviewed into a `ReviewOpening` (`services/review_opening.py`, with a plain `GitRepository` that only reads) and hand it to hosting with a `TerminalAnnouncer`; the agent's commands call an open review through `ReviewClient`. Every value an agent's command takes is checked against the review's own rule as it is parsed (`parameters.py`), so a mistake is a usage error naming the option; `main.py` turns the ordinary failures into one line and lets faults keep their traceback, and loads each command only when it is run, so an agent's command never loads the server or its framework. Whatever the reader or the repository wrote is printed through `terminal_text`, so a terminal's own controls in it are shown, never obeyed; and a text an agent's command takes may be `-`, read from stdin, which is how the skill hands over anything the shell would rewrite.

Dependencies flow inward: cli → hosting → presentation → services → domain, repositories → domain; cli and hosting also use services and repositories directly, to read what is reviewed and to host it

## Code Style

```python
# Domain — pure models, no I/O
class FileStatus(StrEnum):
    MODIFIED = auto()
    ADDED = auto()

# Interfaces — abstract classes the services build on, implemented by inheriting them
class TrackedPaths(ABC):
    @abstractmethod
    async def is_tracked(self, root: Path, relative_path: str) -> bool:
        """Whether the repository tracks the file at this path."""

class GitRepository(ReviewedRepository):
    @override
    async def is_tracked(self, root: Path, relative_path: str) -> bool: ...

# Presentation — FastAPI routes with Depends() DI
@router.post("/submit")
async def submit_review(
    request: SubmitRequest,
    review: Review = Depends(get_review),
) -> SubmitResponse:
    sent = review.submit(threads=[thread.draft() for thread in request.threads], body=request.body, ends=request.end)
    return SubmitResponse(...)
```

## Conventions

- **TDD**: write tests BEFORE implementation. Tests encode functional requirements, not implementation details.
- **Test what the user cares about**: "diff shows all changed files", not "parse_hunk returns a list"
- **Tests and the gates**: the tests are held to formatting alone (`ruff format`, Prettier). No linter, type checker or spelling check reads them — ruff, ty, the code rules, typos, eslint and svelte-check are each told so in their own configuration. vulture and knip read them only for what of the package and the page they use, and report nothing in them. The gates are one list, `.pre-commit-config.yaml`: a commit runs it, and CI's lint job runs it over every file. A hook that cannot run fails and says so — the page's hooks without pnpm among them — and is left out only on purpose, by naming it in `SKIP`, as CI's lint job does for the page's checks its own jobs run.
- **Modules**: `__init__.py` must be empty — no code, no re-exports, nothing
- **Error handling**: specific exceptions, not generic `Exception`. Whatever the review refuses is a `ReviewError` of one kind (`NotFoundError`, `InvalidRequestError`, `RefusedError` ⊃ `TooLargeError`, `ConflictError`, in `domain/exceptions.py`); routes raise it and never catch it or raise `HTTPException` — `presentation/refusals.py` is the one table from kind to status. A refusal says one thing wrong; what is sent whole and may be wrong in many places — a document — is refused with every fault at once, each at its field (`FieldsRefusedError`, a `FieldFault` each), and answered field by field, each fault named under the request's `body`, where FastAPI names a field it refuses itself
- **Time**: every moment the review says is `EpochMillis`, read from the `Clock` the review is built with (`FixedClock` in tests) — never `time.time()` in a route or service. Nothing waits on the clock: a grace period is a timeout on an event, not a comparison of moments
- **Python deps**: add via `uv add` (never specify version), never pip, never manually edit pyproject.toml deps
- **JS deps**: add via `pnpm add` / `pnpm add -D` (never specify version), never manually edit package.json deps
- **TODO/Changelog**: track in `TODO.md` / `CHANGELOG.md`
- **Logging**: DEBUG for timing/perf, INFO for operations, WARNING for recoverable issues, ERROR for failures
- **Type hints**: all function signatures, modern syntax (`str | None`, `list[X]`)
- **Interfaces**: an interface is an abstract class (`ABC`), never a `typing.Protocol` (ruff refuses it): every implementation inherits it, so the type says what the code does. Every member is `@abstractmethod` (ruff's B027 refuses an empty one that is not), so a class that leaves one out cannot be built; each method an implementation writes is marked `@override`, so ty holds it to the interface where it is written — and a parameter the interface asks for that the method does not need is not taken for an unused one
- **Commands**: a click command takes its options keyword-only (`*`): click hands them over by name, and nothing calls a command with a bare `True`
- **Async**: `async`/`await` for all I/O, no sync blocking calls
- **Enums**: use `StrEnum` with `auto()` for all string enumerations
- **A model made from another**: the model makes it itself, in a method that calls its constructor with every field written out — `DiffFile.showing`, `LineAnchor.lost`, `Step.told` — so ty holds the names, the types and the fields it must have. Nothing goes the other way, a model taken apart into its fields by name: `model_copy`, `model_construct`, `model_dump`, `__dict__`, `vars` and `copy.replace` are not used in the package, and the code rules refuse each by name. A model leaves for the wire as JSON (`model_dump_json`; a refusal through `presentation/refusal_answers.py`), never as a mapping. What the rules cannot see by a name — a model handed to `dict(…)`, or walked field by field — the rule forbids all the same. A field with a default left out is what ty cannot see, so each such method is a row of `tests/unit/test_models_made_from_models.py`, which holds what it makes to saying everything its source said; a new one adds its row
- **Wire types**: the browser's types for what crosses the wire are generated from the server's schemas into `frontend/src/lib/types/generated/` — `http.ts` from the routes' OpenAPI, `socket.ts` from a document of the session socket's messages (`presentation/api_schema.py` writes both). Change a schema → run `pnpm api:types`; never edit the generated files by hand. `types/index.ts` names the generated schemas for the rest of the browser. The page makes every HTTP request through `lib/api/request.ts` (eslint refuses `fetch` anywhere else), typed from the generated `paths` by `types/routes.ts`: `read` for a route that answers JSON, `send` for one that answers nothing, `urlOf` for a file the browser fetches itself, as an image is — a path, method, query, body or reply the schema does not have does not compile. A route that answers with a file says so in its schema, as GET /api/images/{image_id} does
- **Test selectors**: use `data-testid` attributes for targeting elements to interact with (click, type, check disabled). Use `getByText` / `text=` only for asserting visible content the user sees. Never use CSS class selectors in tests. Add `data-testid` to every new button, input, textarea, and container.
- **Finding elements in the page's own code**: never by test id or by a page-wide id. An element announces itself to whoever needs it (`FileSections` holds every file section and thread); a selector that cannot be avoided reads a `data-role`, or one of the two attributes that say which of many an element stands for: `data-place`, the line a line number is (where the keyboard and the reading place come back to), and `data-tour`, the name the tour lights a place by. eslint refuses the rest.
- **Frontend layers**: the parts of `frontend/src/lib` build on each other in one direction, as `LAYERS` in `frontend/eslint.config.js` lists them; an import against it fails the lint. Components build on everything and are built on by nothing but components.
- **The API's contract**: every route says in OpenAPI what it takes, what it answers, and how it refuses: each refusal is `{detail}`, in words or field by field, and a route documents every refusal it can give — `responses=refusals(*kinds, takes=...)` names the kinds of `ReviewError` it raises and what it takes in (nothing, parameters, a JSON body or a raw one, which must also be described, as POST /images describes its image), from which `presentation/refusals.py` gives the statuses, those it may be refused for what it takes in marked `x-refused-for-its-input`; the origin guard's 403 is documented on every route. `tests/integration/test_api_refusals.py` holds the refusals a route marks as for its input to exactly what its description says it takes; a yes or a no in a request's or an answer's body is a `WireBool`, `true` or `false` and nothing else (a query parameter is read as FastAPI reads one); a method a route does not take is answered 405 naming every method taken at that path. `tests/integration/test_api_schema.py` has schemathesis draw requests for every route from that schema — the agent's long poll among them, its wait cut short — and hold the answers to it, so a refusal a route gives and does not document fails it; one documented and never given passes it. The server serves its page at `/` and its built assets under `/assets`, nothing more, so a path or a method no route takes is refused by the router.
- **Types on the page**: eslint reads the page with typescript-eslint's strict rules that know types, and the compiler takes a value read from a list or a table by position or key as possibly missing (`noUncheckedIndexedAccess`). Build so that holds rather than checking around it: a line carries its markup instead of sitting beside it in another list, a position the reader is at is the thing they are at (an id), not its place in a list that changes; find, walk or pair things, and reach for an index only where the position is the meaning. A function an interface asks for is written as a property (`label: (anchor: Kind) => string`), so the compiler holds it to its parameter types. eslint reads a `.svelte` import only through Svelte's catch-all declaration, so a component's module script exports nothing another module imports (a type or a function others use lives in a `.ts` module), and a callback handed to a child component or to `<svelte:window>` names its parameter's type; svelte-check holds that type to the prop. What eslint still misreads — `$bindable()`, `{@render}` — and the one place the page trusts the server's JSON are listed in `frontend/eslint.config.js`, each with its reason.
- **Rune state**: an object or array only ever replaced whole — what the server sent, a list rebuilt with `map`/`filter`/spread — is `$state.raw`, never deep `$state`, which wraps every line of a diff in a proxy and pays for it on every read.
- **Styling**: every colour, layer and shadow is written once, in `frontend/src/styles/tokens.css`, for both themes — the tab's icon names its colours by token too, and the page writes their values in as it sets it — and again whenever another theme is applied — an image reading no stylesheet; `main.css` holds the review's `cr-` classes and only names tokens (stylelint refuses the rest). Those classes sit outside Tailwind's layers, so a utility never overrides what a `cr-` class sets on the same element: change it with another `cr-` class, or use the utility instead of the class. Markup carries no `style="…"`: a number only a component knows reaches the stylesheet as `style:--cr-name` (eslint refuses the rest, and any `z-` utility — layers are tokens). Every colour is named by what it means, never by its hue, so a meaning can take another colour in one line of tokens.css: blue is the reader's — what they marked (`--cr-mark`; `--cr-mark-text` as words) and the controls they act with (`--cr-control`: focus rings, keys, buttons, a lit option, the tour's light); violet is the agent's — what it raised, said or brought the reader to (`--cr-agent`), and what of it is not read yet (`--cr-unread`); green and red are what the diff added and removed, and green also what is done (`--cr-done`); yellow a warning; orange a modified file's letter.
- **Panes and keys**: a menu or pane opened from a control is a `Popover` (its look is `PopoverPanel`, with an arrow at the control): it owns the keyboard — in on open, back to what had it on close, closed by Escape, by a press outside, or by the keyboard leaving it. A modal is `Dialog`, a native `<dialog>`, closed with `close()` so the browser restores focus; it is a layer above any pane, so a pane open under it neither closes nor takes what is pressed in it (`Popover`'s `inModalAbove`). The review's keys are rows of `KEYMAP` in `components/keymap.ts`, answered by `pressKey` and listed by the help from the same rows — the field's own chord, Ctrl+Enter (`FIELD_KEYS`), among them. A row says which views its keys are keys of (`views`): what is answered and what is listed are the rows of the view on screen (`keysOf`), so a key that is the files' own — the tree, a file ticked off or folded — does nothing unseen while a story is read; a new view's own key is a row, never a check in a handler. Every reader of keys an editable field can send — the review's own, and each field's — asks `isComposingText` (`dom/keyboard.ts`) first: a key that is building a word in an input method is never the page's. What remains after something is put away, sent or removed takes the keyboard (`focusWhatRemains`), so it is never left on nothing. Moving the reader to a thread, from section to section by `]` and `[`, and to a file the agent names, goes through `Navigator`, which asks the view the review is read in what is walked and where a thread or a file is drawn. A view is a `ReadingView`: `FilesReading` reads the review file by file, and `StoryReading` as the story the agent told of it, where every step and what no step tells is a section of its own; `review.views` (`ReadingViews`) holds both and says which is on screen, which is the review's own state: components ask it by name (`review.views.onScreen.name === 'files'`), never by what it is not. How the reader likes to read is kept with the page's layout and outlives a review; only the switch in the header, shown where the review says a story can be told of it, writes that choice (`choose`), and being taken to something only the files draw changes what is on screen and leaves the choice alone (`showFiles`). Whose numbers the lines of a drawing carry is a `Numbering` (`anchors/numbering.ts`): the review's own, a narrower base's on its left, or another take's — a story stays as it was told when the diff is taken again, so it says the take it was told of and the page holds that against the take it reads (`review.story.numbering`). What hangs on a line's number, a thread or a comment being written, is drawn and taken only where the number is the review's own, so a story the code has moved on from is read, and says so, and takes nothing. No view draws everything by itself: a story draws what it tells and what it leaves out, and the files under a narrower base what that base shows; `threadsNotDrawnIn(view, threads)` is what a view leaves out, counted and offered by whoever shows it. What the view on screen does not draw — a thread on a line no step shows, a file a narrower base leaves out — is gone to where everything is drawn, the files read against the review's own base, which `review.views.showEverything()` brings on screen for it: the one place the whole review is put back for a jump. Whatever takes the reader to a thread or a file — a chip, a notice's list, a key — asks the `Navigator` and widens nothing itself; a failure to put the whole review back is said in the narrowed bar (`review.views.wholeReviewFailed`). The page itself is moved by `FileSections`: a section is known there by the key its view gives it and says which file it draws lines of, so one file may be drawn in several sections, and a line is looked for in each. A file picked in the tree is brought into view by `FileSections` directly, and j and k move the keyboard line by line. A jump lands its file: the `ReadingBand` takes the file jumped to as the one being read (`land`, then `settle`), so v and u act on it. Where the keyboard lands, what a dialog holds and what the layout does are tested in the browser (e2e), which jsdom cannot stand in for; what each key does is tested through `pressKey` in vitest.

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

**Only better, and who says so.** Every change leaves the repository better than it found it — cleaner, more readable, more modular, its architecture more fitting — in every part it touches, not on balance. The rule being written down has not been enough: whoever writes a change can talk themselves into trading it for convenience. So three things hold a change to it, and none is its author's own judgement:

- **The verdict is somebody else's.** A chunk of work is not done, and its author says nothing of it being better, until an independent reviewer has measured its whole diff against this rule, given to it word for word, and listed every place that got worse. That review is part of the chunk, never a favour asked for it.
- **A regression found becomes a gate.** Whatever a review catches is turned into a rule a tool enforces — `scripts/check_code_rules.py`, a linter's rule, a test over the package — so that kind of mistake cannot be made again whatever its author thinks. A form a type checker refused is never answered with a form it cannot see.
- **What its author can name as worse is not committed.** Anything that would be listed under "did not get better" is put right before the commit, or the work stops there and the owner is asked: it is never a note in the report afterwards.

Before presenting work, review every changed file against these principles:

**Clean and readable** — each function does one thing. No god methods. Decompose like existing services do (e.g. `unified_diff` has `_file`, `_path`, `_status`, `_mode`, `_hunks`, `_hunk`).

**Well documented / self-documenting** — names explain intent. Non-obvious patterns get a one-line comment (e.g. `# Only close when clicking the backdrop itself, not the modal content`). Module docstrings explain *why*, not just *what*.

**Functional tests** — tests verify user-facing behavior, not internal data structures. Test names read like requirements: "file content is preserved line by line", not "returns list of DiffLine with type CONTEXT". Compare `tests/integration/test_diff_reading.py` for the standard.

**Modular** — components and services are independently testable. Dependencies are explicit (FastAPI `Depends()`, constructor injection). No hidden coupling between layers.

**No meaningless defaults** — required parameters must be explicit. If a caller must always provide a value, don't give it a default that silently hides bugs. Optional parameters (like `body: str | None = None`) are fine when the absence is a valid state.

**Extensible for future modes** — new review modes (transcript, etc.) should work by adding code, not modifying existing conditionals. Use `isDiffMode` checks (opt-in to diff-specific behavior) rather than `!isFilesMode` checks (which break when a third mode is added). Use lookup maps for mode-dependent values (see `COUNTED_AS` in `FileList.svelte`).

## Commit Messages

Conventional Commits: `type(scope): description`

Types: `feat fix docs style refactor perf test build ci chore`

## Releasing

After any meaningful change, follow this checklist (details in CONTRIBUTING.md):

1. Bump version in `pyproject.toml`, `plugin/.claude-plugin/plugin.json`, and `CHANGELOG.md` (keep in sync)
2. Update skill files if description or usage changed: `plugin/commands/review-ui.md` and `skills/review-ui/SKILL.md`
   And if the release is worth telling a returning reader about, write its entry in `frontend/src/lib/guide/news.ts` under the same version — the review shows it once to whoever last saw an older release
3. Update `README.md` features, `TODO.md` (remove completed items)
4. Commit: `chore: release vX.Y.Z`
5. Push + tag: `git push origin master && git tag vX.Y.Z && git push origin vX.Y.Z` — the tag triggers `release.yml`: full CI suite, artifact verification (`scripts/verify_artifacts.py`), then PyPI publish (tag must match `pyproject.toml` version)
6. After the Release workflow is green, update local skill: `npx skills update review-ui -g -y`
7. Reinstall CLI locally: `uv tool install --upgrade --editable .`

## Documentation

- `README.md` — project overview, usage, installation
- `CHANGELOG.md` — what changed and when
- `TODO.md` — planned work (remove items when done, don't check them off)
- `CONTRIBUTING.md` — dev setup, conventions for contributors
- `SECURITY.md` — vulnerability reporting

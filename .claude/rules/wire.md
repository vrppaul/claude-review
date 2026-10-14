---
paths:
  - "src/claude_review/presentation/**"
  - "frontend/src/lib/types/**"
  - "frontend/src/lib/api/**"
---

# The wire

What crosses between the server, its page and its agent. How a module does its part is said in its docstring; the rules for all of `src/` are in `.claude/rules/server.md`.

## Models and routes

- Every model that crosses the wire is a `WireModel` of its own in `src/claude_review/presentation/wire/`, built from the domain model of the same shape with `.of()`.
- The domain never carries wire settings.
- A wire model may implement an interface the domain holds, where a service asks for what the request carries: a change to a reader's record is a `RecordChange`.
- A yes or a no in a request's or an answer's body is a `WireBool`, `true` or `false` and nothing else. A query parameter is read as FastAPI reads one.
- A number that names a place in a body — a line, an item of a list — is a `WireNumber`, a number and nothing else: read leniently, `false` would name the first.
- A route is thin: it reads the wire, calls one method of the `Review` it gets from `get_review`, and writes the answer.
- A route raises a `ReviewError`, and never catches one or raises `HTTPException`: `src/claude_review/presentation/refusals.py` is the one table from kind to status.

## The API's contract

- Every route says in OpenAPI what it takes, what it answers and how it refuses. Each refusal is `{detail}`, in words or field by field.
- A route documents every refusal it can give: `responses=refusals(*kinds, takes=...)` names the kinds of `ReviewError` it raises and what it takes in — nothing, parameters, a JSON body or a raw one.
- A raw body is described too, as `POST /api/images` describes its image.
- A route that answers with a file says so in its schema, as `GET /api/images/{image_id}` does.
- A refusal a route gives and does not document fails `tests/integration/test_api_schema.py`; one it documents and never gives passes it.

## The page's types and requests

- The page's types for what crosses the wire are generated from the server's schemas into `frontend/src/lib/types/generated/`. Change a schema, then run `pnpm api:types` in `frontend/`.
- Never edit a generated file by hand. `pnpm api:check`, which a hook and CI run, fails when the files no longer match the server.
- The page makes every HTTP request through `frontend/src/lib/api/request.ts`: `read` for a route that answers JSON, `send` for one that answers nothing, `urlOf` for a file the browser fetches itself, as an image is.

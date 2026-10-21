---
paths:
  - "src/claude_review/presentation/**"
  - "frontend/src/lib/types/**"
  - "frontend/src/lib/api/**"
---

# The API

What passes between the server, its page and its agent. How a module does its part is said in its docstring; the rules for all of `src/` are in `.claude/rules/server.md`.

## Schemas and routes

- What a route takes and answers is a `Schema` of its own in `src/claude_review/presentation/schemas/`, apart from the domain's model.
- A schema the review sends is made from the model it carries by its `from_domain()`, and one it takes becomes the domain's by its `to_domain()`: each writes every field out, so ty holds the names.
- A push is made from its page event in `push_of`'s closed match, and a base's words in `src/claude_review/presentation/version_labels.py`.
- The domain never carries the API's settings.
- A schema may implement an interface the domain holds, where a service asks for what the request carries: a change to a reader's record is a `RecordChange`.
- A yes or a no in a request's or an answer's body is pydantic's `StrictBool`, `true` or `false` and nothing else. A query parameter is read as FastAPI reads one.
- A number that names a place in a body — a line, an item of a list — is pydantic's `StrictInt`, a number and nothing else: read leniently, `false` would name the first.
- A route lives in `src/claude_review/presentation/routers/` and is thin: it reads the request, calls one method of the `Review` it is handed as `ReviewDep`, and writes the answer.
- A route raises a `ReviewError`, and never catches one or raises `HTTPException`: `src/claude_review/presentation/errors.py` is the one table from kind to status.

## The API's contract

- Every route says in OpenAPI what it takes, what it answers and how it refuses. Each refusal is `{detail}`, in words or field by field.
- A route documents every refusal it can give: `responses=refusals(*kinds, takes=...)` names the kinds of `ReviewError` it raises and what it takes in — nothing, parameters, a JSON body or a raw one.
- A raw body is described too, as `POST /api/images` describes its image.
- A route that answers with a file says so in its schema, as `GET /api/images/{image_id}` does.
- A refusal a route gives and does not document fails `tests/integration/test_api_schema.py`; one it documents and never gives passes it.

## The page's types and requests

- The page's types for what the API takes and answers are generated from the server's schemas into `frontend/src/lib/types/generated/`. Change a schema, then run `pnpm api:types` in `frontend/`.
- Never edit a generated file by hand. `pnpm api:check`, which a hook and CI run, fails when the files no longer match the server.
- The page makes every HTTP request through `frontend/src/lib/api/request.ts`: `read` for a route that answers JSON, `send` for one that answers nothing, `urlOf` for a file the browser fetches itself, as an image is.

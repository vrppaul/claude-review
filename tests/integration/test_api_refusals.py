"""Every route says how it may be refused, and a refusal is said with the status it is answered with.

What a route raises of its own is held to its word by the schema test, which
fails on any status a route did not describe. What it may be refused for
what it takes in — a field FastAPI finds wrong, a body larger than anything
the review takes — and the origin guard in front of every route are said by
every route they stand before, whether or not a test happens to draw such a
request.
"""

from http import HTTPStatus

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import BaseModel, Field, JsonValue

from claude_review.domain.exceptions import ReviewError
from claude_review.presentation.refusals import answer_refusals, status_of
from claude_review.presentation.wire.refusal import Refusal
from tests.helpers import http_client

# Where the API's description keeps the model every refusal is said in
REFUSAL_SCHEMA = f"#/components/schemas/{Refusal.__name__}"
# Why the test route refuses, whatever kind it raises
REASON = "refused for the test"
REFUSING_ROUTE = "/refuse/{kind_name}"


class SchemaReference(BaseModel):
    """A schema the description points at rather than spells out, if it does."""

    reference: str | None = Field(default=None, alias="$ref")


class MediaType(BaseModel):
    """What one answer is written as, in one media type."""

    schema_reference: SchemaReference = Field(alias="schema")


class Answer(BaseModel):
    """One answer an operation describes."""

    content: dict[str, MediaType] = Field(default_factory=dict)

    def is_refusal(self) -> bool:
        """Whether the answer is a refusal, said as every refusal is."""
        return any(media.schema_reference.reference == REFUSAL_SCHEMA for media in self.content.values())


class Operation(BaseModel):
    """What the test reads of one operation in the API's description: what it takes in, and what it answers."""

    parameters: list[JsonValue] = Field(default_factory=list)
    request_body: JsonValue = Field(default=None, alias="requestBody")
    responses: dict[str, Answer]

    def refuses_with(self, status: HTTPStatus) -> bool:
        """Whether the operation says it may answer with this status, as a refusal."""
        answer = self.responses.get(str(status.value))
        return answer is not None and answer.is_refusal()


class Description(BaseModel):
    """The API's description, as far as the test reads it: every operation of every path."""

    paths: dict[str, dict[str, Operation]]

    def operations(self) -> dict[str, Operation]:
        """Every operation, named by its method and path."""
        return {
            f"{method.upper()} {path}": operation
            for path, operations in self.paths.items()
            for method, operation in operations.items()
        }


def every_kind_of(kind: type[ReviewError]) -> list[type[ReviewError]]:
    """The kinds of refusal under a kind, however deep."""
    return [descendant for child in kind.__subclasses__() for descendant in [child, *every_kind_of(child)]]


# Every kind of refusal the review raises, by name
REFUSAL_KINDS = {kind.__name__: kind for kind in every_kind_of(ReviewError)}


async def refuse(kind_name: str) -> None:
    """A route that refuses with whichever kind it is asked for."""
    raise REFUSAL_KINDS[kind_name](REASON)


@pytest.fixture
async def described(client: AsyncClient) -> Description:
    return Description.model_validate((await client.get("/openapi.json")).json())


def _unsaid(status: HTTPStatus, *, among: dict[str, Operation]) -> list[str]:
    """The operations among these that do not say they may refuse with the status."""
    return [name for name, operation in among.items() if not operation.refuses_with(status)]


def test_every_route_says_the_origin_guard_may_refuse_it(described: Description) -> None:
    assert _unsaid(HTTPStatus.FORBIDDEN, among=described.operations()) == []


def test_every_route_that_takes_anything_in_says_it_may_refuse_what_it_had_wrong(described: Description) -> None:
    taking_in = {
        name: operation
        for name, operation in described.operations().items()
        if operation.parameters or operation.request_body is not None
    }

    assert _unsaid(HTTPStatus.UNPROCESSABLE_CONTENT, among=taking_in) == []


@pytest.mark.parametrize(
    "refused", [HTTPStatus.CONTENT_TOO_LARGE, HTTPStatus.BAD_REQUEST], ids=["too large", "unreadable"]
)
def test_every_route_that_reads_a_body_says_it_may_refuse_one_too_large_or_unreadable(
    described: Description, refused: HTTPStatus
) -> None:
    """Too large for anything the review takes, or bytes FastAPI cannot read as JSON at all: not even text."""
    reading_a_body = {
        name: operation for name, operation in described.operations().items() if operation.request_body is not None
    }

    assert _unsaid(refused, among=reading_a_body) == []


@pytest.mark.parametrize("kind_name", sorted(REFUSAL_KINDS))
async def test_a_refusal_is_described_with_the_status_it_is_answered_with(kind_name: str) -> None:
    """A kind of refusal is answered as the nearest kind the table names, and described the same way."""
    app = FastAPI()
    answer_refusals(app)
    app.add_api_route(REFUSING_ROUTE, refuse)

    async with http_client(app) as caller:
        answered = await caller.get(REFUSING_ROUTE.format(kind_name=kind_name))

    assert answered.status_code == status_of(REFUSAL_KINDS[kind_name])

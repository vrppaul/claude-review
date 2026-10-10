"""Every route says how it may be refused, and a refusal is said with the status it is answered with.

What a route is refused on the way, for what it takes in — a field FastAPI
finds wrong, a body it cannot read, one larger than anything the review
takes — is said by exactly the routes that take such things, and by no
other; the origin guard's refusal by every route it stands before. What a
route raises of its own is held to its word only where the schema test's
requests reach it: that test fails on any status a route did not describe.
"""

from http import HTTPStatus

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import BaseModel, Field, JsonValue

from claude_review.domain.exceptions import ReviewError
from claude_review.presentation.refusals import ON_THE_WAY_NOTE, REFUSED_ON_THE_WAY, Takes, answer_refusals, status_of
from claude_review.presentation.wire.refusal import Refusal
from tests.helpers import http_client

# Where the API's description keeps the model every refusal is said in
REFUSAL_SCHEMA = f"#/components/schemas/{Refusal.__name__}"
# Why the test route refuses, whatever kind it raises
REASON = "refused for the test"
REFUSING_ROUTE = "/refuse/{kind_name}"
# The body FastAPI reads as JSON and checks against a model
JSON_MEDIA_TYPE = "application/json"


class SchemaReference(BaseModel):
    """A schema the description points at rather than spells out, if it does."""

    reference: str | None = Field(default=None, alias="$ref")


class MediaType(BaseModel):
    """What one answer is written as, in one media type."""

    schema_reference: SchemaReference = Field(alias="schema")


class Answer(BaseModel):
    """One answer an operation describes."""

    description: str
    content: dict[str, MediaType] = Field(default_factory=dict)

    def is_refusal(self) -> bool:
        """Whether the answer is a refusal, said as every refusal is."""
        return any(media.schema_reference.reference == REFUSAL_SCHEMA for media in self.content.values())


class RequestBody(BaseModel):
    """The body an operation is sent, by the media types it may come in."""

    content: dict[str, JsonValue]


class Operation(BaseModel):
    """What the test reads of one operation in the API's description: what it takes in, and what it answers."""

    parameters: list[JsonValue] = Field(default_factory=list)
    request_body: RequestBody | None = Field(default=None, alias="requestBody")
    responses: dict[str, Answer]

    def refuses_with(self, status: HTTPStatus) -> bool:
        """Whether the operation says it may answer with this status, as a refusal."""
        answer = self.responses.get(str(status.value))
        return answer is not None and answer.is_refusal()

    def takes(self) -> Takes:
        """What the operation takes in, as the description says: a body, JSON or not, parameters, or nothing."""
        if self.request_body is not None:
            return Takes.JSON_BODY if JSON_MEDIA_TYPE in self.request_body.content else Takes.RAW_BODY
        return Takes.PARAMETERS if self.parameters else Takes.NOTHING

    def refused_on_the_way(self) -> frozenset[HTTPStatus]:
        """The refusals the operation says it may meet before its route is reached."""
        return frozenset(
            HTTPStatus(int(status))
            for status, answer in self.responses.items()
            if answer.is_refusal() and answer.description.endswith(ON_THE_WAY_NOTE)
        )


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


def test_what_a_route_is_refused_on_the_way_is_what_it_takes_in_and_no_more(described: Description) -> None:
    """A route taking nothing says it meets no such refusal; one taking parameters or a body, exactly those it may."""
    unlike = {
        name: sorted(operation.refused_on_the_way())
        for name, operation in described.operations().items()
        if operation.refused_on_the_way() != REFUSED_ON_THE_WAY[operation.takes()]
    }

    assert unlike == {}


@pytest.mark.parametrize("kind_name", sorted(REFUSAL_KINDS))
async def test_a_refusal_is_described_with_the_status_it_is_answered_with(kind_name: str) -> None:
    """A kind of refusal is answered as the nearest kind the table names, and described the same way."""
    app = FastAPI()
    answer_refusals(app)
    app.add_api_route(REFUSING_ROUTE, refuse)

    async with http_client(app) as caller:
        answered = await caller.get(REFUSING_ROUTE.format(kind_name=kind_name))

    assert answered.status_code == status_of(REFUSAL_KINDS[kind_name])

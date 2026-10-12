"""Every route says how it may be refused, and a refusal is said with the status it is answered with.

What a route is refused on the way, for what it takes in — a field FastAPI
finds wrong, a body it cannot read, one larger than anything the review
takes — is said by exactly the routes that take such things, and by no
other; the origin guard's refusal by every route it stands before. What a
route raises of its own is held to its word only where the schema test's
requests reach it: that test fails on any status a route did not describe.
"""

import importlib
import pkgutil
from functools import partial
from http import HTTPStatus

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import BaseModel, Field

import claude_review
from claude_review.domain import exceptions
from claude_review.domain.exceptions import FieldFault, FieldsRefusedError, ReviewError
from claude_review.presentation.api_schema import http_document
from claude_review.presentation.origin_guard import NOT_ITS_PAGE_STATUS
from claude_review.presentation.refusals import (
    INPUT_REFUSAL_EXTENSION,
    REFUSED_FOR_INPUT,
    Takes,
    answer_refusals,
    status_of,
)
from claude_review.presentation.wire.refusal import FieldRefusal, Refusal
from claude_review.services.image_service import IMAGE_FORMATS
from tests.helpers import IMAGES_ROUTE, http_client

# Where the API's description keeps the model every refusal is said in
REFUSAL_SCHEMA = f"#/components/schemas/{Refusal.__name__}"
# Why the test route refuses, whatever kind it raises
REASON = "refused for the test"
REFUSING_ROUTE = "/refuse/{kind_name}"
# The body FastAPI reads as JSON and checks against a model
JSON_MEDIA_TYPE = "application/json"
# The types of which no value is refused unless something bounds it: any text, or nothing at all
UNBOUNDED_TYPES = {"string", "null"}
# Where a parameter that is part of the path sits: it is never missing, though the description calls it required
PATH_LOCATION = "path"
# A JSON body no route takes: every route's body is an object
NOT_AN_OBJECT: list[object] = []
# What a refusal says of a field, and nothing more: never the value the caller sent, which it has
SAID_OF_A_FIELD = set(FieldRefusal.model_fields)


class SchemaReference(BaseModel):
    """A schema the description points at rather than spells out, if it does."""

    reference: str | None = Field(default=None, alias="$ref")


class MediaType(BaseModel):
    """What one answer is written as, in one media type."""

    schema_reference: SchemaReference = Field(alias="schema")


class Answer(BaseModel):
    """One answer an operation describes."""

    content: dict[str, MediaType] = Field(default_factory=dict)
    refused_for_input: bool = Field(default=False, alias=INPUT_REFUSAL_EXTENSION)

    def is_refusal(self) -> bool:
        """Whether the answer is a refusal, said as every refusal is."""
        return any(media.schema_reference.reference == REFUSAL_SCHEMA for media in self.content.values())


class RequestBody(BaseModel):
    """The body an operation is sent, by the media types it may come in."""

    required: bool = False
    content: dict[str, MediaType]


class ParameterSchema(BaseModel):
    """What the test reads of a parameter's schema: its type, and what bounds it."""

    type: str | None = None
    max_length: int | None = Field(default=None, alias="maxLength")
    min_length: int | None = Field(default=None, alias="minLength")
    pattern: str | None = None
    any_of: list[ParameterSchema] = Field(default_factory=list, alias="anyOf")

    def can_be_wrong(self) -> bool:
        """Whether some value sent for it would be refused: any but a bare string, or a string bound some way."""
        if self.any_of:
            return any(option.can_be_wrong() for option in self.any_of)
        if self.type in UNBOUNDED_TYPES:
            return any(bound is not None for bound in (self.max_length, self.min_length, self.pattern))
        return True


class Parameter(BaseModel):
    """One parameter of an operation: whether it must be sent, and what it may be."""

    location: str = Field(alias="in")
    required: bool = False
    schema_: ParameterSchema = Field(alias="schema")

    def can_be_refused(self) -> bool:
        """Whether FastAPI may refuse the request for it: missing when it must be sent, or wrong."""
        can_be_missing = self.required and self.location != PATH_LOCATION
        return can_be_missing or self.schema_.can_be_wrong()


class Operation(BaseModel):
    """What the test reads of one operation in the API's description: what it takes in, and what it answers."""

    parameters: list[Parameter] = Field(default_factory=list)
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
        return Takes.PARAMETERS if any(parameter.can_be_refused() for parameter in self.parameters) else Takes.NOTHING

    def refused_for_input(self) -> frozenset[HTTPStatus]:
        """The refusals the operation says it may give for what it takes in."""
        return frozenset(
            HTTPStatus(int(status))
            for status, answer in self.responses.items()
            if answer.is_refusal() and answer.refused_for_input
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
# The kinds that carry what they found wrong, field by field, and what the test's refusals of those kinds found
KINDS_WITH_FIELDS = [FieldsRefusedError, *every_kind_of(FieldsRefusedError)]
FAULTS = [
    FieldFault(path=("chapters", 0, "title"), reason="says nothing"),
    FieldFault(path=("housekeeping", 1), reason="is no file of this change"),
]
# How the test makes a refusal of each kind: with its reason, and with its faults when it carries them
REFUSALS = {
    **{name: partial(kind, REASON) for name, kind in REFUSAL_KINDS.items()},
    **{kind.__name__: partial(kind, REASON, FAULTS) for kind in KINDS_WITH_FIELDS},
}


async def refuse(kind_name: str) -> None:
    """A route that refuses with whichever kind it is asked for."""
    raise REFUSALS[kind_name]()


@pytest.fixture
def described() -> Description:
    return Description.model_validate(http_document())


@pytest.fixture
def refusing() -> FastAPI:
    """An app whose one route refuses with whichever kind it is asked for, answered as the review answers."""
    app = FastAPI()
    answer_refusals(app)
    app.add_api_route(REFUSING_ROUTE, refuse)
    return app


def _unsaid(status: HTTPStatus, *, among: dict[str, Operation]) -> list[str]:
    """The operations among these that do not say they may refuse with the status."""
    return [name for name, operation in among.items() if not operation.refuses_with(status)]


def test_every_route_says_the_origin_guard_may_refuse_it(described: Description) -> None:
    assert _unsaid(NOT_ITS_PAGE_STATUS, among=described.operations()) == []


def test_an_image_upload_says_it_takes_an_image_in_every_format_the_review_keeps(described: Description) -> None:
    """Said, a client knows what to send, and the schema test sends it images."""
    upload = described.operations()[f"POST {IMAGES_ROUTE}"]

    assert upload.request_body is not None
    assert upload.request_body.required
    assert set(upload.request_body.content) == {known.media_type for known in IMAGE_FORMATS}


def test_what_a_route_is_refused_for_what_it_takes_in_is_what_it_takes_in_and_no_more(
    described: Description,
) -> None:
    """A route taking nothing says it meets no such refusal; one taking parameters or a body, exactly those it may."""
    unlike = {
        name: sorted(operation.refused_for_input())
        for name, operation in described.operations().items()
        if operation.refused_for_input() != REFUSED_FOR_INPUT[operation.takes()]
    }

    assert unlike == {}


@pytest.mark.parametrize("kind_name", sorted(REFUSAL_KINDS))
async def test_a_refusal_is_described_with_the_status_it_is_answered_with(kind_name: str, refusing: FastAPI) -> None:
    """A kind of refusal is answered as the nearest kind the table names, and described the same way."""
    async with http_client(refusing) as caller:
        answered = await caller.get(REFUSING_ROUTE.format(kind_name=kind_name))

    assert answered.status_code == status_of(REFUSAL_KINDS[kind_name])


def test_every_kind_of_refusal_is_kept_where_the_review_keeps_its_refusals() -> None:
    """A kind written anywhere else is one this test never reads: answered, and held to nothing here."""
    for module in pkgutil.walk_packages(claude_review.__path__, prefix=f"{claude_review.__name__}."):
        importlib.import_module(module.name)

    assert {kind.__module__ for kind in every_kind_of(ReviewError)} == {exceptions.__name__}


@pytest.mark.parametrize("kind", KINDS_WITH_FIELDS, ids=[kind.__name__ for kind in KINDS_WITH_FIELDS])
async def test_a_refusal_that_carries_what_it_found_wrong_is_answered_field_by_field(
    kind: type[FieldsRefusedError], refusing: FastAPI
) -> None:
    """Each fault where it was found and why, as a request FastAPI finds wrong is answered: one shape, whoever refused."""
    async with http_client(refusing) as caller:
        answered = await caller.get(REFUSING_ROUTE.format(kind_name=kind.__name__))

    assert Refusal.model_validate(answered.json()) == Refusal(
        detail=[FieldRefusal(loc=fault.path, msg=fault.reason) for fault in FAULTS]
    )


def _taking_json(described: Description) -> list[tuple[str, str]]:
    """Every operation that takes a JSON body, as its method and path."""
    return [
        (method, path)
        for path, operations in described.paths.items()
        for method, operation in operations.items()
        if operation.takes() == Takes.JSON_BODY
    ]


async def test_a_body_a_route_finds_wrong_is_refused_field_by_field(
    described: Description, client: AsyncClient
) -> None:
    """Where each field was wrong and why, as the contract says a refusal is: the page and the agent both name them."""
    refused = {
        f"{method.upper()} {path}": await client.request(method, path, json=NOT_AN_OBJECT)
        for method, path in _taking_json(described)
    }

    assert refused, "no route takes a JSON body"
    assert {name: answer.status_code for name, answer in refused.items()} == dict.fromkeys(
        refused, HTTPStatus.UNPROCESSABLE_CONTENT
    )
    for name, answer in refused.items():
        said = answer.json()
        assert set(said) == {"detail"}, name
        assert said["detail"], name
        assert all(set(field) == SAID_OF_A_FIELD for field in said["detail"]), name

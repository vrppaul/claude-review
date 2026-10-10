"""Every route, sent what its schema allows and what it does not: none of it is a fault of the server's.

Schemathesis reads the review's own OpenAPI and draws requests for each
route, the well formed and the malformed alike. Whatever it sends, the
review answers or refuses — never a fault of its own — refuses what the
schema does not allow, answers with the shapes and statuses the schema
gives, and turns a method a route does not take away naming those it does.
"""

import pytest
import schemathesis
from fastapi import FastAPI
from schemathesis import Case
from schemathesis.checks import CheckFunction
from schemathesis.specs.openapi.checks import positive_data_acceptance

from tests.helpers import EVENTS_ROUTE, LOCAL_HEADERS, LOCAL_ORIGIN, ReviewFactory, one_line_file, opening_of

# What the review holds a well-formed request to beyond its schema, which no
# schema can say: that what it names — a thread, a file, a base — is in the
# review, that a range starts before it ends, that a message says something
BEYOND_THE_SCHEMA: list[CheckFunction] = [positive_data_acceptance]

# The agent's long poll waits out whatever it is asked to, up to ten minutes
schema = schemathesis.pytest.from_fixture("served_schema").exclude(path=EVENTS_ROUTE)


class ReviewsByOperation:
    """A review for each operation drawn against, built the first time it is asked for.

    What one operation does — sending the review for good, ending it — must
    not decide what the next one is sent to.
    """

    def __init__(self, reviews: ReviewFactory) -> None:
        self._reviews = reviews
        self._apps: dict[str, FastAPI] = {}

    def app_for(self, operation: str) -> FastAPI:
        if operation not in self._apps:
            self._apps[operation] = self._reviews.app(opening_of([one_line_file()]))
        return self._apps[operation]


@pytest.fixture
def served_schema(reviews: ReviewFactory) -> schemathesis.BaseSchema:
    return schemathesis.openapi.from_asgi(
        "/openapi.json", reviews.app(opening_of([one_line_file()])), headers=LOCAL_HEADERS
    )


@pytest.fixture
def reviews_by_operation(reviews: ReviewFactory) -> ReviewsByOperation:
    return ReviewsByOperation(reviews)


@schema.parametrize()
def test_whatever_a_route_is_sent_it_answers_as_its_schema_says(
    case: Case, reviews_by_operation: ReviewsByOperation
) -> None:
    case.call_and_validate(
        app=reviews_by_operation.app_for(case.operation.label),
        base_url=LOCAL_ORIGIN,
        headers=LOCAL_HEADERS,
        excluded_checks=BEYOND_THE_SCHEMA,
    )

"""Every route, sent what its schema allows and what it does not: none of it is a fault of the server's.

Schemathesis reads the review's own OpenAPI and draws requests for each
route, the well formed and the malformed alike. Whatever it sends, the
review answers or refuses — never a fault of its own — refuses what the
schema does not allow, answers with the shape the schema gives, and turns a
method a route does not take away as a router should.
"""

import pytest
import schemathesis
from schemathesis import Case
from schemathesis.checks import CheckFunction
from schemathesis.specs.openapi.checks import allow_header_conformance, positive_data_acceptance

from tests.helpers import LOCAL_HEADERS, LOCAL_ORIGIN, ReviewFactory, one_line_file

# What the review holds a request to beyond its schema, and so not checked
# against the schema alone: a well-formed request may still name a thread, a
# file or a base the review does not hold, which only the review can refuse;
# and a route that takes GET takes HEAD too, which no schema lists
BEYOND_THE_SCHEMA: list[CheckFunction] = [positive_data_acceptance, allow_header_conformance]
# The agent's long poll: asked for up to ten minutes, it waits them out
WAITS_FOR_THE_READER = "/api/wait"

schema = schemathesis.pytest.from_fixture("served_schema")


@pytest.fixture
def served_schema(reviews: ReviewFactory) -> schemathesis.BaseSchema:
    app = reviews.app([one_line_file()])
    return schemathesis.openapi.from_asgi("/openapi.json", app, headers=LOCAL_HEADERS).exclude(
        path=WAITS_FOR_THE_READER
    )


@schema.parametrize()
def test_whatever_a_route_is_sent_it_answers_as_its_schema_says(case: Case) -> None:
    case.call_and_validate(base_url=LOCAL_ORIGIN, headers=LOCAL_HEADERS, excluded_checks=BEYOND_THE_SCHEMA)

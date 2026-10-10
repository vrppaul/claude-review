"""Every route, sent what its schema allows and what it does not: none of it is a fault of the server's.

Schemathesis reads the review's own OpenAPI and draws requests for each
route, the well formed and the malformed alike. Whatever it sends, the
review answers or refuses — never a fault of its own — refuses what the
schema does not allow, answers with the shapes and statuses the schema
gives, and turns a method a route does not take away naming those it does.
"""

from pathlib import Path

import pytest
import schemathesis
from fastapi import FastAPI
from schemathesis import Case
from schemathesis.checks import CheckFunction
from schemathesis.specs.openapi.checks import positive_data_acceptance

from claude_review.services.review_opening import ReviewOpening
from tests.helpers import EVENTS_ROUTE, LOCAL_HEADERS, LOCAL_ORIGIN, ReviewFactory, one_line_file, opening_of

# What the review holds a well-formed request to beyond its schema, which no
# schema can say: that what it names — a thread, a file, a base — is in the
# review, that a range starts before it ends, that a message says something
BEYOND_THE_SCHEMA: list[CheckFunction] = [positive_data_acceptance]

# The agent's long poll waits out whatever it is asked to, up to ten minutes
schema = schemathesis.pytest.from_fixture("served_schema").exclude(path=EVENTS_ROUTE)

# What the repository under review has changed since its commit: a file
# edited and a file added, so its diff, its files and its retake have
# something to show
EDITED_FILE = "initial.txt"
ADDED_FILE = "src/added.py"
EDITED_TEXT = "initial content\nand a line since\n"
ADDED_TEXT = "def added() -> None:\n    return None\n"


class ReviewsByOperation:
    """A review for each operation drawn against, built the first time it is asked for.

    What one operation does — sending the review for good, ending it — must
    not decide what the next one is sent to.
    """

    def __init__(self, reviews: ReviewFactory, opening: ReviewOpening) -> None:
        self._reviews = reviews
        self._opening = opening
        self._apps: dict[str, FastAPI] = {}

    def app_for(self, operation: str) -> FastAPI:
        if operation not in self._apps:
            self._apps[operation] = self._reviews.app(self._opening)
        return self._apps[operation]


@pytest.fixture
def changed_repository(tmp_git_repo: Path) -> Path:
    (tmp_git_repo / EDITED_FILE).write_text(EDITED_TEXT)
    (tmp_git_repo / ADDED_FILE).parent.mkdir()
    (tmp_git_repo / ADDED_FILE).write_text(ADDED_TEXT)
    return tmp_git_repo


@pytest.fixture
def served_schema(reviews: ReviewFactory) -> schemathesis.BaseSchema:
    return schemathesis.openapi.from_asgi(
        "/openapi.json", reviews.app(opening_of([one_line_file()])), headers=LOCAL_HEADERS
    )


@pytest.fixture
def reviews_read_once(reviews: ReviewFactory) -> ReviewsByOperation:
    """Reviews of files read once: no bases, no context to widen, nothing to take again."""
    return ReviewsByOperation(reviews, opening_of([one_line_file()]))


@pytest.fixture
def reviews_of_a_repository(reviews: ReviewFactory, changed_repository: Path) -> ReviewsByOperation:
    """Reviews of a repository's changes, which git is asked about whenever a route needs it."""
    return ReviewsByOperation(reviews, opening_of([], root=changed_repository))


def _answers_as_its_schema_says(case: Case, reviews_by_operation: ReviewsByOperation) -> None:
    case.call_and_validate(
        app=reviews_by_operation.app_for(case.operation.label),
        base_url=LOCAL_ORIGIN,
        headers=LOCAL_HEADERS,
        excluded_checks=BEYOND_THE_SCHEMA,
    )


@schema.parametrize()
def test_whatever_a_route_is_sent_it_answers_as_its_schema_says(
    case: Case, reviews_read_once: ReviewsByOperation
) -> None:
    _answers_as_its_schema_says(case, reviews_read_once)


@schema.parametrize()
def test_a_review_of_a_repository_answers_whatever_it_is_sent_as_its_schema_says(
    case: Case, reviews_of_a_repository: ReviewsByOperation
) -> None:
    """Bases, wider context and retakes reach git here: nothing git says may become a fault."""
    _answers_as_its_schema_says(case, reviews_of_a_repository)

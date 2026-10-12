"""Every route, sent what its schema allows and what it does not: none of it is a fault of the server's.

Schemathesis reads the review's own OpenAPI, as the page's types are
written from it, and draws requests for each route, the well formed and the
malformed alike. Whatever it sends, the review answers or refuses — never a
fault of its own — refuses what the schema does not allow, answers with the
shapes and statuses the schema gives, and turns a method a route does not
take away naming those it does. The agent's poll for events is drawn as
every other route is, its wait cut to a moment.
"""

from pathlib import Path

import pytest
import schemathesis
from fastapi import FastAPI
from schemathesis import Case
from schemathesis.checks import CheckFunction
from schemathesis.specs.openapi.checks import positive_data_acceptance

from claude_review.hosting.hosted_review import HostedReview
from claude_review.presentation.api_schema import http_document
from claude_review.presentation.wire.base import MAX_WAIT_SECONDS
from claude_review.services.image_service import IMAGE_FORMATS
from claude_review.services.review_opening import ReviewOpening
from tests.helpers import (
    EVENTS_ROUTE,
    LOCAL_HEADERS,
    LOCAL_ORIGIN,
    ReviewFactory,
    one_line_file,
    opening_of,
    repository_opening,
)

# What the review holds a well-formed request to beyond its schema, which no
# schema can say: that what it names — a thread, a file, a base — is in the
# review, that a range starts before it ends, that a message says something
BEYOND_THE_SCHEMA: list[CheckFunction] = [positive_data_acceptance]

schema = schemathesis.pytest.from_fixture("described_schema")

# The agent's long poll waits out whatever it is asked to, up to ten
# minutes: a wait drawn within its bounds is cut to this, and one drawn
# outside them is left as drawn, to be refused
LONGEST_DRAWN_WAIT_SECONDS = 0.001
WAIT_PARAMETER = "wait_seconds"

# An image is uploaded as its bytes, as any binary body is sent
BINARY_MEDIA_TYPE = "application/octet-stream"
schemathesis.serializer.alias([known.media_type for known in IMAGE_FORMATS], BINARY_MEDIA_TYPE)

# What the repository under review has changed since its commit: a file
# edited and a file added, so its diff, its files and its retake have
# something to show
EDITED_FILE = "initial.txt"
ADDED_FILE = "src/added.py"
EDITED_TEXT = "initial content\nand a line since\n"
ADDED_TEXT = "def added() -> None:\n    return None\n"


class ReviewsByOperation:
    """A review for each operation drawn against, built the first time it is asked for and again once it is over.

    What one operation does must not decide what the next one is sent to.
    A round sent for good ends its review, and every round drawn after it
    would be refused as sent to a review that is over: the round's writing
    would be reached once a run, by whichever round came first.
    """

    def __init__(self, reviews: ReviewFactory, opening: ReviewOpening) -> None:
        self._reviews = reviews
        self._opening = opening
        self._hosted: dict[str, HostedReview] = {}

    def app_for(self, operation: str) -> FastAPI:
        hosted = self._hosted.get(operation)
        if hosted is None or hosted.review.lifetime.has_ended:
            hosted = self._reviews.hosted(self._opening)
            self._hosted[operation] = hosted
        return hosted.app


@pytest.fixture
def changed_repository(tmp_git_repo: Path) -> Path:
    (tmp_git_repo / EDITED_FILE).write_text(EDITED_TEXT)
    (tmp_git_repo / ADDED_FILE).parent.mkdir()
    (tmp_git_repo / ADDED_FILE).write_text(ADDED_TEXT)
    return tmp_git_repo


@pytest.fixture
def described_schema() -> schemathesis.BaseSchema:
    """The API as the page's types are written from it: in-process, since the review serves no description of it."""
    return schemathesis.openapi.from_dict(http_document())


@pytest.fixture
def reviews_read_once(reviews: ReviewFactory) -> ReviewsByOperation:
    """Reviews of files read once: no bases, no context to widen, nothing to take again."""
    return ReviewsByOperation(reviews, opening_of([one_line_file()]))


@pytest.fixture
async def reviews_of_a_repository(reviews: ReviewFactory, changed_repository: Path) -> ReviewsByOperation:
    """Reviews of a repository's changes, which git is asked about whenever a route needs it."""
    return ReviewsByOperation(reviews, await repository_opening(changed_repository))


def _seconds_drawn(value: object) -> float | None:
    """A wait as the route reads it from the query — drawn as a number or as its text — or None for anything else."""
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _cut_to_a_moment(drawn: object) -> object:
    """A wait the route takes, cut to a moment; one it refuses, left to be refused.

    A wait drawn several times over is read by the route as its last, so the
    last is the one cut.
    """
    if isinstance(drawn, list):
        return [*drawn[:-1], _cut_to_a_moment(drawn[-1])] if drawn else drawn
    seconds = _seconds_drawn(drawn)
    if seconds is None or not 0 < seconds <= MAX_WAIT_SECONDS:
        return drawn
    return min(seconds, LONGEST_DRAWN_WAIT_SECONDS)


def _a_moment_at_most(query: dict[str, object] | None) -> dict[str, object]:
    """A poll's query with its wait cut to a moment.

    A poll that names no wait waits the route's own, which is as long as any
    other it takes.
    """
    drawn = query or {}
    if WAIT_PARAMETER not in drawn:
        return {**drawn, WAIT_PARAMETER: LONGEST_DRAWN_WAIT_SECONDS}
    return {**drawn, WAIT_PARAMETER: _cut_to_a_moment(drawn[WAIT_PARAMETER])}


def _answers_as_its_schema_says(case: Case, reviews_by_operation: ReviewsByOperation) -> None:
    if case.operation.path == EVENTS_ROUTE:
        case.query = _a_moment_at_most(case.query)
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

"""How the agent's client tells what a review answered: a refusal said in a line, naming the field as typed."""

import contextlib
import threading
from collections.abc import Generator
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from claude_review.cli.review_client import FieldRefusal, Refusal, ReviewCallError, ReviewClient
from claude_review.hosting.address import LOOPBACK
from claude_review.hosting.ports import ANY_FREE_PORT
from claude_review.presentation.schemas import ShowRequest

# A refusal as FastAPI writes one for a field it would not take, under the
# part of the request the field came in
FIELD_REFUSED = Refusal(detail=[FieldRefusal(loc=("body", "file"), msg="String should have at least 1 character")])
# A refusal the review says in its own words
REFUSED_IN_WORDS = Refusal(detail="No such file in this review")
SHOWN = ShowRequest(file="src/a.py")


class RefusingReview(HTTPServer):
    """A review that refuses whatever it is sent, always with the same answer."""

    def __init__(self, answer: Refusal) -> None:
        super().__init__((LOOPBACK, ANY_FREE_PORT), RefusingHandler)
        self.answer = answer.model_dump_json().encode()


class RefusingHandler(BaseHTTPRequestHandler):
    """The answer the refusing review gives every request."""

    def do_POST(self) -> None:
        assert isinstance(self.server, RefusingReview)
        answer = self.server.answer
        self.send_response(HTTPStatus.UNPROCESSABLE_ENTITY)
        self.send_header("Content-Length", str(len(answer)))
        self.end_headers()
        self.wfile.write(answer)

    def log_message(self, format: str, *args: object) -> None:
        """Quiet: what it answers is what the test reads."""


@contextlib.contextmanager
def _refusing_review(answer: Refusal) -> Generator[ReviewClient]:
    """A client of a review that refuses everything, for as long as the block runs."""
    review = RefusingReview(answer)
    serving = threading.Thread(target=review.serve_forever, daemon=True)
    serving.start()
    try:
        yield ReviewClient(review.server_address[1])
    finally:
        review.shutdown()
        review.server_close()


def test_a_field_the_review_refuses_is_named_as_it_was_typed() -> None:
    """The part of the request it came in says nothing to whoever typed the command."""
    with _refusing_review(FIELD_REFUSED) as client, pytest.raises(ReviewCallError) as refused:
        client.show(SHOWN)

    assert str(refused.value).endswith("file: String should have at least 1 character")
    assert "body" not in str(refused.value)


def test_a_refusal_in_words_is_passed_on_as_said() -> None:
    with _refusing_review(REFUSED_IN_WORDS) as client, pytest.raises(ReviewCallError) as refused:
        client.show(SHOWN)

    assert str(refused.value).endswith("No such file in this review")
    assert str(HTTPStatus.UNPROCESSABLE_ENTITY.value) in str(refused.value)

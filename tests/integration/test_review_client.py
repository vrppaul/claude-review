"""How the agent's client speaks to a review: what it sends arrives as said, and a refusal is said in a line."""

import asyncio
import contextlib
import threading
from collections.abc import Generator
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import override

import pytest
from httpx import AsyncClient

from claude_review.cli.review_client import ReviewCallError, ReviewClient
from claude_review.hosting.address import LOOPBACK
from claude_review.hosting.ports import ANY_FREE_PORT
from claude_review.presentation.wire.agent import ProgressRequest, SayRequest, ShowRequest, StatusRequest
from claude_review.presentation.wire.content import ReviewResponse
from claude_review.presentation.wire.refusal import FieldRefusal, Refusal
from tests.helpers import REVIEW_ROUTE, ReviewServers, one_line_file, opening_of

# A refusal as FastAPI writes one for a field it would not take, under the
# part of the request the field came in
FIELD_REFUSED = Refusal(detail=[FieldRefusal(loc=("body", "file"), msg="String should have at least 1 character")])
# A refusal the review says in its own words
REFUSED_IN_WORDS = Refusal(detail="No such file in this review")
SHOWN = ShowRequest(file="src/a.py")

# What an agent says in the reader's own language: accents, Cyrillic, a dash,
# curly quotes, an emoji — and a file named in it too
SAID_BEYOND_ASCII = "Готово — café “green” 🙂"
FILE_BEYOND_ASCII = "src/ж.py"
CONTEXT_BEYOND_ASCII = "53 % — почти полон"


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
        self.send_response(HTTPStatus.UNPROCESSABLE_CONTENT)
        self.send_header("Content-Length", str(len(answer)))
        self.end_headers()
        self.wfile.write(answer)

    @override
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
    assert str(HTTPStatus.UNPROCESSABLE_CONTENT.value) in str(refused.value)


async def test_what_the_agent_says_beyond_ascii_reaches_the_review_as_said(servers: ReviewServers) -> None:
    """An agent answers in the reader's language, and a file may be named in it."""
    review = await servers.start(opening_of([one_line_file(FILE_BEYOND_ASCII)]))
    agent = ReviewClient(review.port)

    # The client blocks while the review, on this very loop, answers it
    await asyncio.to_thread(agent.say, SayRequest(body=SAID_BEYOND_ASCII, files=[FILE_BEYOND_ASCII]))
    await asyncio.to_thread(agent.report_progress, ProgressRequest(text=SAID_BEYOND_ASCII, files=[FILE_BEYOND_ASCII]))
    await asyncio.to_thread(agent.report_status, StatusRequest(context=CONTEXT_BEYOND_ASCII))
    seen = await asyncio.to_thread(agent.catch_up)
    async with AsyncClient(base_url=review.url) as page:
        facts = ReviewResponse.model_validate_json((await page.get(REVIEW_ROUTE)).content)

    assert [entry.body for entry in seen.panel] == [SAID_BEYOND_ASCII]
    assert seen.agent.context == CONTEXT_BEYOND_ASCII
    assert facts.work is not None
    assert (facts.work.text, facts.work.files) == (SAID_BEYOND_ASCII, [FILE_BEYOND_ASCII])

"""The server answers its own page and nothing else.

It binds to loopback with no authentication, which is only safe while
loopback means "this machine, this page". A page on any domain can point
that domain at 127.0.0.1 and the browser will then treat this server as
same-origin; the same-origin policy never applies to WebSockets at all; and
a page next door reads without CORS — an image, a `no-cors` fetch — sending
no Origin, which only the browser's word on where a request comes from
gives away.
"""

from http import HTTPStatus

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from httpx import AsyncClient

from claude_review.presentation.schemas.pushes import ShowPush
from claude_review.presentation.schemas.refusal import Refusal
from tests.helpers import (
    DIFF_ROUTE,
    EVENTS_ROUTE,
    GLANCE_AT_EVENTS,
    LOCAL_HOST,
    LOCAL_ORIGIN,
    REVIEW_ROUTE,
    REVIEWED_FILE,
    ReviewFactory,
    next_push,
    one_line_file,
    open_session,
)

FOREIGN_HEADERS = {"Origin": "https://attacker.example", "Host": LOCAL_HOST}
# Another server on this machine: a dev server, a notebook, a page any package can start
NEIGHBOUR_HEADERS = {"Origin": "http://localhost:5173", "Host": LOCAL_HOST}
# The same, on the very address the review is served at: only the port tells them apart
NEIGHBOUR_ON_THE_SAME_ADDRESS_HEADERS = {"Origin": "http://127.0.0.1:5173", "Host": LOCAL_HOST}
# The review's own page, opened by the machine's name rather than its address,
# as a browser that says where a request comes from sends it
LOCALHOST_PAGE_HEADERS = {"Origin": "http://localhost:8000", "Host": "localhost:8000", "Sec-Fetch-Site": "same-origin"}

# The header in which a browser says where a request comes from (Fetch Metadata),
# and what it says of a page on another port of this machine and of one anywhere else
FETCH_SITE = "Sec-Fetch-Site"
ANOTHER_PORT = "same-site"
ANOTHER_SITE = "cross-site"
# What a browser says of a request from the page itself, and of one no page
# made: an address typed, a bookmark opened
SAME_PAGE = "same-origin"
NO_PAGE = "none"

# What the reader typed in the panel, for the agent to pick up
A_MESSAGE = {"message_id": "panel-1", "body": "Is the retry still needed?", "images": []}
# A file the page's build might have put beside it
A_PAGE_FILE = "/assets/index.js"


async def test_a_rebound_domain_is_refused(client: AsyncClient) -> None:
    """The name the page asked for is in the Host header, and it is not ours."""
    response = await client.get(DIFF_ROUTE, headers={"Host": "attacker.example"})

    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.parametrize(
    "origin",
    ["http://[", "http://127.0.0.1:8000/", "https://127.0.0.1:8000"],
    ids=["no-address", "a-path-after-it", "a-scheme-the-review-is-not-served-over"],
)
async def test_an_origin_not_written_as_the_reviews_own_is_refused_not_a_fault(
    client: AsyncClient, origin: str
) -> None:
    response = await client.get(DIFF_ROUTE, headers={"Origin": origin})

    assert response.status_code == HTTPStatus.FORBIDDEN


async def test_a_page_on_another_site_cannot_read_the_diff(client: AsyncClient) -> None:
    response = await client.get(DIFF_ROUTE, headers={"Origin": "https://attacker.example"})

    assert response.status_code == HTTPStatus.FORBIDDEN
    # Said as every refusal is said, so a caller reads one shape whoever refused
    assert Refusal.model_validate_json(response.content).detail


async def test_the_reviews_own_page_is_allowed(client: AsyncClient) -> None:
    response = await client.get(DIFF_ROUTE, headers={"Origin": LOCAL_ORIGIN})

    assert response.status_code == HTTPStatus.OK


async def test_a_page_on_another_port_of_this_machine_cannot_read_the_diff(client: AsyncClient) -> None:
    """Loopback is not one page: any local server's page is a different origin."""
    response = await client.get(DIFF_ROUTE, headers=NEIGHBOUR_HEADERS)

    assert response.status_code == HTTPStatus.FORBIDDEN


async def test_a_page_on_the_same_address_and_another_port_cannot_read_the_diff(client: AsyncClient) -> None:
    """The port is part of the origin: 127.0.0.1 serves the page next door too."""
    response = await client.get(DIFF_ROUTE, headers=NEIGHBOUR_ON_THE_SAME_ADDRESS_HEADERS)

    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.parametrize("fetch_site", [ANOTHER_PORT, ANOTHER_SITE])
async def test_a_page_elsewhere_cannot_read_the_review_by_a_request_that_sends_no_origin(
    client: AsyncClient, fetch_site: str
) -> None:
    """An image or a `no-cors` fetch carries no Origin; the browser still says it came from another page."""
    response = await client.get(DIFF_ROUTE, headers={FETCH_SITE: fetch_site})

    assert response.status_code == HTTPStatus.FORBIDDEN


async def test_a_page_on_another_port_cannot_take_what_the_reader_handed_the_agent(client: AsyncClient) -> None:
    """Nor make the review think an agent is there, so offering the reader rounds nobody will answer."""
    await client.post("/api/message", json=A_MESSAGE)

    taken = await client.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS, headers={FETCH_SITE: ANOTHER_PORT})
    attached = (await client.get(REVIEW_ROUTE)).json()["answerer_attached"]
    event = (await client.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()

    assert taken.status_code == HTTPStatus.FORBIDDEN
    assert attached is False
    assert event["message"]["body"] == A_MESSAGE["body"]


@pytest.mark.parametrize(
    "headers",
    [{FETCH_SITE: SAME_PAGE, "Origin": LOCAL_ORIGIN}, {FETCH_SITE: NO_PAGE}],
    ids=["from-its-own-page", "from-no-page"],
)
async def test_what_the_browser_says_came_from_the_page_itself_or_from_no_page_is_answered(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    response = await client.get(DIFF_ROUTE, headers=headers)

    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize("path", ["/", A_PAGE_FILE])
async def test_a_link_from_another_site_still_opens_the_page(client: AsyncClient, path: str) -> None:
    """Following a link is a request from another site; the page and its files hold nothing of the review."""
    response = await client.get(path, headers={FETCH_SITE: ANOTHER_SITE})

    assert response.status_code != HTTPStatus.FORBIDDEN


async def test_a_page_without_an_origin_of_its_own_is_refused(client: AsyncClient) -> None:
    """A sandboxed frame or a file page says "null"; it is nobody's page."""
    response = await client.get(DIFF_ROUTE, headers={"Origin": "null"})

    assert response.status_code == HTTPStatus.FORBIDDEN


async def test_the_reviews_own_page_over_ipv6_loopback_is_allowed(client: AsyncClient) -> None:
    response = await client.get(DIFF_ROUTE, headers={"Origin": "http://[::1]:8000", "Host": "[::1]:8000"})

    assert response.status_code == HTTPStatus.OK


async def test_a_command_line_client_has_no_origin_and_is_allowed(client: AsyncClient) -> None:
    """`claude-review wait` is not a browser and sends no Origin."""
    response = await client.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)

    assert response.status_code == HTTPStatus.OK


def test_a_page_on_another_site_cannot_open_the_session_socket(review_page: TestClient) -> None:
    """Without this the page could read what the server pushes, and end the
    review by connecting and disconnecting once."""
    # Starlette raises when the handshake is refused before it becomes a socket
    with pytest.raises(WebSocketDisconnect), open_session(review_page, FOREIGN_HEADERS):
        pass


@pytest.mark.parametrize(
    "headers",
    [
        NEIGHBOUR_HEADERS,
        NEIGHBOUR_ON_THE_SAME_ADDRESS_HEADERS,
        # The review's own page as the browser names it, asked for under a rebound name
        {"Origin": LOCAL_ORIGIN, "Host": "attacker.example"},
    ],
    ids=["another-local-port", "another-port-of-the-same-address", "foreign-host"],
)
def test_only_the_reviews_own_page_opens_the_session_socket(headers: dict[str, str], review_page: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect), open_session(review_page, headers):
        pass


def test_a_socket_the_browser_says_another_page_opened_is_refused(reviews: ReviewFactory) -> None:
    """Whatever Origin it sends: the browser's word on where it comes from is enough."""
    with (
        TestClient(reviews.app_of_change([one_line_file()]), base_url=LOCAL_ORIGIN) as browser,
        pytest.raises(WebSocketDisconnect),
        open_session(browser, {"Host": LOCAL_HOST, FETCH_SITE: ANOTHER_PORT}),
    ):
        pass


def test_the_reviews_own_page_opened_as_localhost_holds_the_session_socket(review_page: TestClient) -> None:
    """The same machine by name: the socket opens, and what the server says reaches it."""
    with open_session(review_page, LOCALHOST_PAGE_HEADERS) as socket:
        review_page.post("/api/show", json={"file": REVIEWED_FILE})

        assert next_push(socket, ShowPush) == ShowPush(file=REVIEWED_FILE)


async def test_the_page_says_what_it_may_load(client: AsyncClient) -> None:
    """It loads nothing from anywhere else, so it can say so."""
    policy = (await client.get(DIFF_ROUTE)).headers["content-security-policy"]

    assert "default-src 'none'" in policy
    assert "connect-src 'self'" in policy


@pytest.mark.parametrize("headers", [{}, FOREIGN_HEADERS], ids=["an-answer", "the-guards-refusal"])
async def test_every_answer_says_what_a_browser_may_do_with_it_refusals_included(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    """A refusal reaches a browser as any answer does: read as what it says it is, framed by nobody, leaking no address."""
    answered = (await client.get(DIFF_ROUTE, headers=headers)).headers

    assert answered["x-content-type-options"] == "nosniff"
    assert answered["referrer-policy"] == "no-referrer"
    assert answered["x-frame-options"] == "DENY"
    assert "default-src 'none'" in answered["content-security-policy"]


async def test_the_review_cannot_be_framed(client: AsyncClient) -> None:
    """Framing it would let a page bait a click on Send and end the review."""
    headers = (await client.get(DIFF_ROUTE)).headers

    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert headers["x-frame-options"] == "DENY"

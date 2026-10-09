"""The server answers its own page and nothing else.

It binds to loopback with no authentication, which is only safe while
loopback means "this machine, this page". A page on any domain can point
that domain at 127.0.0.1 and the browser will then treat this server as
same-origin; and the same-origin policy never applies to WebSockets at all.
"""

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from httpx import AsyncClient

from claude_review.presentation.wire.pushes import PushKind
from tests.helpers import (
    DIFF_ROUTE,
    EVENTS_ROUTE,
    GLANCE_AT_EVENTS,
    LOCAL_HOST,
    LOCAL_ORIGIN,
    REVIEWED_FILE,
    next_push,
    open_session,
)

FOREIGN_HEADERS = {"Origin": "https://attacker.example", "Host": LOCAL_HOST}
# Another server on this machine: a dev server, a notebook, a page any package can start
NEIGHBOUR_HEADERS = {"Origin": "http://localhost:5173", "Host": LOCAL_HOST}
# The review's own page, opened by the machine's name rather than its address
LOCALHOST_PAGE_HEADERS = {"Origin": "http://localhost:8000", "Host": "localhost:8000"}


async def test_the_review_answers_its_own_page(client: AsyncClient) -> None:
    assert (await client.get(DIFF_ROUTE)).status_code == 200


async def test_a_rebound_domain_is_refused(client: AsyncClient) -> None:
    """The name the page asked for is in the Host header, and it is not ours."""
    response = await client.get(DIFF_ROUTE, headers={"Host": "attacker.example"})

    assert response.status_code == 403


async def test_localhost_is_the_same_machine(client: AsyncClient) -> None:
    assert (await client.get(DIFF_ROUTE, headers={"Host": "localhost:8000"})).status_code == 200


async def test_a_page_on_another_site_cannot_read_the_diff(client: AsyncClient) -> None:
    response = await client.get(DIFF_ROUTE, headers={"Origin": "https://attacker.example"})

    assert response.status_code == 403


async def test_a_page_on_another_site_cannot_end_the_review(client: AsyncClient) -> None:
    response = await client.post(
        "/api/submit",
        json={"threads": [], "end": True},
        headers={"Origin": "https://attacker.example"},
    )

    assert response.status_code == 403


async def test_the_reviews_own_page_is_allowed(client: AsyncClient) -> None:
    response = await client.get(DIFF_ROUTE, headers={"Origin": LOCAL_ORIGIN})

    assert response.status_code == 200


async def test_a_page_on_another_port_of_this_machine_cannot_read_the_diff(client: AsyncClient) -> None:
    """Loopback is not one page: any local server's page is a different origin."""
    response = await client.get(DIFF_ROUTE, headers=NEIGHBOUR_HEADERS)

    assert response.status_code == 403


async def test_a_page_on_another_port_of_this_machine_cannot_end_the_review(client: AsyncClient) -> None:
    response = await client.post("/api/end", headers=NEIGHBOUR_HEADERS)

    assert response.status_code == 403


async def test_a_page_without_an_origin_of_its_own_is_refused(client: AsyncClient) -> None:
    """A sandboxed frame or a file page says "null"; it is nobody's page."""
    response = await client.get(DIFF_ROUTE, headers={"Origin": "null"})

    assert response.status_code == 403


async def test_the_reviews_own_page_over_ipv6_loopback_is_allowed(client: AsyncClient) -> None:
    response = await client.get(DIFF_ROUTE, headers={"Origin": "http://[::1]:8000", "Host": "[::1]:8000"})

    assert response.status_code == 200


async def test_a_command_line_client_has_no_origin_and_is_allowed(client: AsyncClient) -> None:
    """`claude-review wait` is not a browser and sends no Origin."""
    response = await client.get(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)

    assert response.status_code == 200


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
        # The review's own page as the browser names it, asked for under a rebound name
        {"Origin": LOCAL_ORIGIN, "Host": "attacker.example"},
    ],
    ids=["another-local-port", "foreign-host"],
)
def test_only_the_reviews_own_page_opens_the_session_socket(headers: dict[str, str], review_page: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect), open_session(review_page, headers):
        pass


def test_the_reviews_own_page_opened_as_localhost_holds_the_session_socket(review_page: TestClient) -> None:
    """The same machine by name: the socket opens, and what the server says reaches it."""
    with open_session(review_page, LOCALHOST_PAGE_HEADERS) as socket:
        review_page.post("/api/show", json={"file": REVIEWED_FILE})

        assert next_push(socket, PushKind.SHOW) == {"type": "show", "file": REVIEWED_FILE}


async def test_the_page_says_what_it_may_load(client: AsyncClient) -> None:
    """It loads nothing from anywhere else, so it can say so."""
    policy = (await client.get(DIFF_ROUTE)).headers["content-security-policy"]

    assert "default-src 'none'" in policy
    assert "connect-src 'self'" in policy


async def test_the_review_cannot_be_framed(client: AsyncClient) -> None:
    """Framing it would let a page bait a click on Send and end the review."""
    headers = (await client.get(DIFF_ROUTE)).headers

    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert headers["x-frame-options"] == "DENY"

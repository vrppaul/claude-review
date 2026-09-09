"""The server answers its own page and nothing else.

It binds to loopback with no authentication, which is only safe while
loopback means "this machine, this page". A page on any domain can point
that domain at 127.0.0.1 and the browser will then treat this server as
same-origin; and the same-origin policy never applies to WebSockets at all.
"""

import asyncio

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from claude_review.domain.models import (
    DiffFile,
    DiffHunk,
    DiffLine,
    FileStatus,
    LineType,
    ReviewMode,
)
from claude_review.presentation.app import create_app
from claude_review.presentation.state import ServerState

FOREIGN_HEADERS = {"Origin": "https://attacker.example", "Host": "127.0.0.1:8000"}


@pytest.fixture
def state() -> ServerState:
    return ServerState(shutdown_event=asyncio.Event())


def _files() -> list[DiffFile]:
    return [
        DiffFile(
            path="a.py",
            status=FileStatus.MODIFIED,
            hunks=[
                DiffHunk(
                    header="@@ -1 +1 @@",
                    old_start=1,
                    new_start=1,
                    lines=[DiffLine(type=LineType.CONTEXT, old_no=1, new_no=1, content="x = 1")],
                )
            ],
        )
    ]


@pytest.fixture
async def client(state: ServerState):
    app = create_app(diff_files=_files(), state=state, mode=ReviewMode.DIFF)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1:8000") as ac:
        yield ac


async def test_the_review_answers_its_own_page(client: AsyncClient) -> None:
    assert (await client.get("/api/diff")).status_code == 200


async def test_a_rebound_domain_is_refused(client: AsyncClient) -> None:
    """The name the page asked for is in the Host header, and it is not ours."""
    response = await client.get("/api/diff", headers={"Host": "attacker.example"})

    assert response.status_code == 403


async def test_localhost_is_the_same_machine(client: AsyncClient) -> None:
    assert (await client.get("/api/diff", headers={"Host": "localhost:8000"})).status_code == 200


async def test_a_page_on_another_site_cannot_read_the_diff(client: AsyncClient) -> None:
    response = await client.get("/api/diff", headers={"Origin": "https://attacker.example"})

    assert response.status_code == 403


async def test_a_page_on_another_site_cannot_end_the_review(client: AsyncClient) -> None:
    response = await client.post(
        "/api/submit",
        json={"comments": []},
        headers={"Origin": "https://attacker.example"},
    )

    assert response.status_code == 403


async def test_a_command_line_client_has_no_origin_and_is_allowed(client: AsyncClient) -> None:
    """`claude-review wait` is not a browser and sends no Origin."""
    response = await client.get("/api/events", params={"wait_seconds": 0.1})

    assert response.status_code == 200


def test_a_page_on_another_site_cannot_open_the_session_socket(state: ServerState) -> None:
    """Without this the page could read what the server pushes, and end the
    review by connecting and disconnecting once."""
    client = TestClient(create_app(diff_files=_files(), state=state, mode=ReviewMode.DIFF))

    # Starlette raises when the handshake is refused before it becomes a socket
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect("/api/session", headers=FOREIGN_HEADERS),
    ):
        pass


def test_a_refused_socket_does_not_count_as_a_reader_leaving(state: ServerState) -> None:
    """A refused handshake must not make the server think the review closed."""
    client = TestClient(create_app(diff_files=_files(), state=state, mode=ReviewMode.DIFF))

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect("/api/session", headers=FOREIGN_HEADERS),
    ):
        pass

    assert not state.browser_gone(now=1e12, grace=3.0)


async def test_the_page_says_what_it_may_load(client: AsyncClient) -> None:
    """It loads nothing from anywhere else, so it can say so."""
    policy = (await client.get("/api/diff")).headers["content-security-policy"]

    assert "default-src 'none'" in policy
    assert "connect-src 'self'" in policy


async def test_the_review_cannot_be_framed(client: AsyncClient) -> None:
    """Framing it would let a page bait a click on Send and end the review."""
    headers = (await client.get("/api/diff")).headers

    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert headers["x-frame-options"] == "DENY"

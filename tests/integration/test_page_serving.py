"""The page and the files its build put beside it: served as far as they were built, and nothing else."""

from http import HTTPStatus
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from claude_review.presentation.app import ASSETS_NAME, PAGE_NAME, serve_the_page

# What a build of the page left, in a test's own folder
BUILT_PAGE = "<html>the review</html>"
BUILT_SCRIPT = "console.log('drawn')"
SCRIPT_NAME = "page.js"


@pytest.fixture
def built(tmp_path: Path) -> Path:
    (tmp_path / PAGE_NAME).write_text(BUILT_PAGE)
    (tmp_path / ASSETS_NAME).mkdir()
    (tmp_path / ASSETS_NAME / SCRIPT_NAME).write_text(BUILT_SCRIPT)
    return tmp_path


def _served(built: Path) -> TestClient:
    app = FastAPI()
    serve_the_page(app, built)
    return TestClient(app)


def test_the_page_and_the_files_beside_it_are_served(built: Path) -> None:
    client = _served(built)

    assert client.get("/").text == BUILT_PAGE
    assert client.get(f"/{ASSETS_NAME}/{SCRIPT_NAME}").text == BUILT_SCRIPT


def test_a_checkout_whose_page_was_never_built_still_serves_its_routes(tmp_path: Path) -> None:
    """A checkout with no pnpm builds no page; the review must still start, and say there is none."""
    assert _served(tmp_path).get("/").status_code == HTTPStatus.NOT_FOUND


def test_a_socket_opened_among_the_page_files_is_turned_away_not_a_fault(built: Path) -> None:
    with (
        pytest.raises(WebSocketDisconnect),
        _served(built).websocket_connect(f"/{ASSETS_NAME}/{SCRIPT_NAME}") as socket,
    ):
        socket.receive_text()

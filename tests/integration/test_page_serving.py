"""The page and the files its build put beside it: served as far as they were built, and nothing else."""

import base64
import hashlib
from http import HTTPMethod, HTTPStatus
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from claude_review.presentation.app import ASSETS_NAME, PAGE_NAME, serve_the_page
from claude_review.presentation.refusals import answer_refusals
from tests.helpers import methods_allowed

# What a build of the page left, in a test's own folder
BUILT_PAGE = "<html>the review</html>"
BUILT_SCRIPT = "console.log('drawn')"
SCRIPT_NAME = "page.js"
# What the review's page runs inline before its files arrive, as its build
# writes it: the theme, so the first paint is never in the wrong one
THEME_SCRIPT = """
      // The theme — before the first paint
      document.documentElement.setAttribute("data-theme", "dark");
    """
ANOTHER_THEME_SCRIPT = """
      document.documentElement.setAttribute("data-theme", "light");
    """
# The header the page says what it may run in
POLICY_HEADER = "content-security-policy"


@pytest.fixture
def built(tmp_path: Path) -> Path:
    (tmp_path / PAGE_NAME).write_text(BUILT_PAGE)
    (tmp_path / ASSETS_NAME).mkdir()
    (tmp_path / ASSETS_NAME / SCRIPT_NAME).write_text(BUILT_SCRIPT)
    return tmp_path


def _page_running(inline_script: str) -> str:
    """A built page that runs a script inline, then its built files."""
    return f'<html><head><script>{inline_script}</script><script type="module" src="/assets/{SCRIPT_NAME}"></script></head></html>'


def _named_by_hash(script: str) -> str:
    """A script as a policy names one by its hash: SHA-256 of its text as UTF-8, in base 64."""
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    return f"'sha256-{digest}'"


def _script_sources(policy: str) -> list[str]:
    """Where a policy lets scripts come from."""
    directives = [directive.split() for directive in policy.split(";")]
    return next(sources for name, *sources in directives if name == "script-src")


def _built_page(folder: Path, page: str) -> Path:
    (folder / PAGE_NAME).write_text(page, encoding="utf-8")
    return folder


def _served(built: Path) -> TestClient:
    app = FastAPI()
    answer_refusals(app)
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


def test_a_method_the_page_files_do_not_take_is_refused_naming_those_they_do(built: Path) -> None:
    """A file is fetched or asked about, and nothing else; the refusal says so, as every refusal of a method does."""
    response = _served(built).put(f"/{ASSETS_NAME}/{SCRIPT_NAME}")

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert methods_allowed(response) == {HTTPMethod.GET, HTTPMethod.HEAD}


def test_the_page_runs_its_own_inline_script_named_by_its_hash_and_no_other(tmp_path: Path) -> None:
    """Injected markup runs nothing: no inline script runs unless the page itself carries it."""
    policy = _served(_built_page(tmp_path, _page_running(THEME_SCRIPT))).get("/").headers[POLICY_HEADER]

    assert _script_sources(policy) == ["'self'", _named_by_hash(THEME_SCRIPT)]
    assert "'unsafe-inline'" not in _script_sources(policy)


def test_a_page_built_again_runs_its_new_inline_script_and_not_the_old_one(tmp_path: Path) -> None:
    """The hash is taken from the page as served, never written down beside it."""
    client = _served(_built_page(tmp_path, _page_running(THEME_SCRIPT)))
    _built_page(tmp_path, _page_running(ANOTHER_THEME_SCRIPT))

    policy = client.get("/").headers[POLICY_HEADER]

    assert _script_sources(policy) == ["'self'", _named_by_hash(ANOTHER_THEME_SCRIPT)]


def test_a_page_with_no_inline_script_runs_its_built_files_alone(built: Path) -> None:
    policy = _served(built).get("/").headers[POLICY_HEADER]

    assert _script_sources(policy) == ["'self'"]


@pytest.mark.parametrize("line_end", ["\r\n", "\r"], ids=["carriage-return-line-feed", "carriage-return"])
def test_a_page_built_with_other_line_ends_names_its_script_as_a_browser_reads_it(
    tmp_path: Path, line_end: str
) -> None:
    """A browser reads every line end as a line feed before it hashes a script."""
    (tmp_path / PAGE_NAME).write_bytes(_page_running(THEME_SCRIPT).replace("\n", line_end).encode())

    policy = _served(tmp_path).get("/").headers[POLICY_HEADER]

    assert _named_by_hash(THEME_SCRIPT) in _script_sources(policy)

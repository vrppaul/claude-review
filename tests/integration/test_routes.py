"""API contract tests for the presentation layer."""

import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, LineType, ReviewMode
from claude_review.presentation.app import create_app
from claude_review.presentation.schemas import ServerState
from claude_review.services.text_file_service import TextFileService


@pytest.fixture
def mock_diff_files() -> list[DiffFile]:
    return [
        DiffFile(
            path="src/handler.ts",
            status=FileStatus.MODIFIED,
            hunks=[
                DiffHunk(
                    header="@@ -1,3 +1,4 @@",
                    old_start=1,
                    new_start=1,
                    lines=[
                        DiffLine(type=LineType.CONTEXT, old_no=1, new_no=1, content="const x = 1;"),
                        DiffLine(type=LineType.DELETE, old_no=2, new_no=None, content="const y = 2;"),
                        DiffLine(type=LineType.ADD, old_no=None, new_no=2, content="const y = 3;"),
                        DiffLine(type=LineType.ADD, old_no=None, new_no=3, content="const z = 4;"),
                        DiffLine(type=LineType.CONTEXT, old_no=3, new_no=4, content="export { x };"),
                    ],
                )
            ],
        )
    ]


@pytest.fixture
def server_state() -> ServerState:
    return ServerState(shutdown_event=asyncio.Event())


@pytest.fixture
async def client(mock_diff_files: list[DiffFile], server_state: ServerState):
    app = create_app(diff_files=mock_diff_files, state=server_state, mode=ReviewMode.DIFF)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_get_diff_returns_files_json(client: AsyncClient) -> None:
    """GET /api/diff returns diff data matching the schema."""
    response = await client.get("/api/diff")

    assert response.status_code == 200
    data = response.json()
    assert "files" in data
    assert data["mode"] == "diff"
    assert len(data["files"]) == 1
    assert data["files"][0]["path"] == "src/handler.ts"
    assert data["files"][0]["status"] == "modified"
    assert len(data["files"][0]["hunks"]) == 1
    assert len(data["files"][0]["hunks"][0]["lines"]) == 5


async def test_get_diff_line_types_correct(client: AsyncClient) -> None:
    """Lines in the response have correct types and line numbers."""
    response = await client.get("/api/diff")
    lines = response.json()["files"][0]["hunks"][0]["lines"]

    context = lines[0]
    assert context["type"] == "context"
    assert context["old_no"] == 1
    assert context["new_no"] == 1

    delete = lines[1]
    assert delete["type"] == "delete"
    assert delete["old_no"] == 2
    assert delete["new_no"] is None

    add = lines[2]
    assert add["type"] == "add"
    assert add["old_no"] is None
    assert add["new_no"] == 2


async def test_submit_with_comments_returns_formatted_markdown(
    client: AsyncClient,
) -> None:
    """POST /api/submit returns formatted review markdown."""
    response = await client.post(
        "/api/submit",
        json={
            "comments": [
                {"file": "src/handler.ts", "start_line": 42, "end_line": 42, "body": "Wrong null check"},
                {"file": "src/handler.ts", "start_line": 67, "end_line": 70, "body": "Add max retry"},
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["comment_count"] == 2
    assert "### src/handler.ts:42" in data["markdown"]
    assert "### src/handler.ts:67-70" in data["markdown"]
    assert "Wrong null check" in data["markdown"]
    assert "Add max retry" in data["markdown"]


async def test_submit_with_empty_comments(client: AsyncClient) -> None:
    """POST /api/submit with no comments returns clean response."""
    response = await client.post("/api/submit", json={"comments": []})

    assert response.status_code == 200
    data = response.json()
    assert data["comment_count"] == 0
    assert data["markdown"] == ""


async def test_submit_triggers_shutdown_signal(client: AsyncClient, server_state: ServerState) -> None:
    """POST /api/submit sets the shutdown event."""
    assert not server_state.shutdown_event.is_set()

    await client.post(
        "/api/submit",
        json={"comments": [{"file": "x.py", "start_line": 1, "end_line": 1, "body": "note"}]},
    )

    assert server_state.shutdown_event.is_set()


async def test_double_submit_returns_409(client: AsyncClient) -> None:
    """Second submit returns 409 Conflict."""
    payload = {"comments": [{"file": "x.py", "start_line": 1, "end_line": 1, "body": "note"}]}

    first = await client.post("/api/submit", json=payload)
    assert first.status_code == 200

    second = await client.post("/api/submit", json=payload)
    assert second.status_code == 409


async def test_submit_stores_result_in_state(client: AsyncClient, server_state: ServerState) -> None:
    """POST /api/submit stores formatted markdown in state.result."""
    assert server_state.result is None

    await client.post(
        "/api/submit",
        json={"comments": [{"file": "x.py", "start_line": 1, "end_line": 1, "body": "fix this"}]},
    )

    assert server_state.result is not None
    assert "fix this" in server_state.result


async def test_heartbeat_updates_state(client: AsyncClient, server_state: ServerState) -> None:
    """POST /api/heartbeat records a timestamp in state."""
    assert server_state.last_heartbeat is None

    response = await client.post("/api/heartbeat")

    assert response.status_code == 200
    assert server_state.last_heartbeat is not None
    assert server_state.last_heartbeat > 0


async def test_submit_rejects_invalid_comment(client: AsyncClient) -> None:
    """POST /api/submit with invalid comment data returns 422."""
    # Empty body
    response = await client.post(
        "/api/submit",
        json={"comments": [{"file": "x.py", "start_line": 1, "end_line": 1, "body": ""}]},
    )
    assert response.status_code == 422

    # start_line > end_line
    response = await client.post(
        "/api/submit",
        json={"comments": [{"file": "x.py", "start_line": 10, "end_line": 5, "body": "note"}]},
    )
    assert response.status_code == 422

    # Negative line number
    response = await client.post(
        "/api/submit",
        json={"comments": [{"file": "x.py", "start_line": 0, "end_line": 1, "body": "note"}]},
    )
    assert response.status_code == 422


# --- Review body tests ---


async def test_submit_with_body_only(client: AsyncClient, server_state: ServerState) -> None:
    """Submit with review body but no inline comments."""
    response = await client.post(
        "/api/submit",
        json={"comments": [], "body": "Wrong approach, reconsider the design."},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["comment_count"] == 1
    assert "Wrong approach" in data["markdown"]
    assert server_state.shutdown_event.is_set()


async def test_submit_with_body_and_comments(client: AsyncClient) -> None:
    """Submit with both review body and inline comments."""
    response = await client.post(
        "/api/submit",
        json={
            "comments": [
                {"file": "x.py", "start_line": 1, "end_line": 1, "body": "Fix this"},
            ],
            "body": "Generally good, one issue.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["comment_count"] == 2
    # Body appears before inline comment
    body_pos = data["markdown"].index("Generally good")
    inline_pos = data["markdown"].index("### x.py:1")
    assert body_pos < inline_pos


# --- Files mode tests ---


@pytest.fixture
def plan_file(tmp_path: Path) -> Path:
    """A real text file for files-mode integration tests."""
    f = tmp_path / "plan.md"
    f.write_text("# My Plan\n\nStep one\nStep two\n")
    return f


@pytest.fixture
async def files_mode_client(plan_file: Path, server_state: ServerState):
    """Client backed by a real text file loaded through TextFileService."""
    diff_files = TextFileService().read_files([plan_file])
    app = create_app(diff_files=diff_files, state=server_state, mode=ReviewMode.FILES)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_files_mode_api_reports_mode(files_mode_client: AsyncClient) -> None:
    """The API tells the frontend which mode to render."""
    response = await files_mode_client.get("/api/diff")

    assert response.status_code == 200
    assert response.json()["mode"] == "files"


async def test_files_mode_review_round_trip(
    files_mode_client: AsyncClient,
    plan_file: Path,
    server_state: ServerState,
) -> None:
    """Load a text file, comment on a specific line, submit — verify output."""
    # Get the file path as the service resolved it
    data = (await files_mode_client.get("/api/diff")).json()
    file_path = data["files"][0]["path"]

    # Comment on line 3 ("Step one")
    response = await files_mode_client.post(
        "/api/submit",
        json={
            "comments": [
                {"file": file_path, "start_line": 3, "end_line": 3, "body": "Needs more detail"},
            ]
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["comment_count"] == 1
    assert f"### {file_path}:3" in result["markdown"]
    assert "Needs more detail" in result["markdown"]
    assert server_state.shutdown_event.is_set()

"""API contract tests for the presentation layer."""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, LineType
from claude_review.presentation.app import create_app


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
def shutdown_event() -> asyncio.Event:
    return asyncio.Event()


@pytest.fixture
async def client(mock_diff_files: list[DiffFile], shutdown_event: asyncio.Event):
    app = create_app(diff_files=mock_diff_files, shutdown_event=shutdown_event)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_get_diff_returns_files_json(client: AsyncClient) -> None:
    """GET /api/diff returns diff data matching the schema."""
    response = await client.get("/api/diff")

    assert response.status_code == 200
    data = response.json()
    assert "files" in data
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


async def test_submit_triggers_shutdown_signal(client: AsyncClient, shutdown_event: asyncio.Event) -> None:
    """POST /api/submit sets the shutdown event."""
    assert not shutdown_event.is_set()

    await client.post(
        "/api/submit",
        json={"comments": [{"file": "x.py", "start_line": 1, "end_line": 1, "body": "note"}]},
    )

    assert shutdown_event.is_set()


async def test_double_submit_returns_409(client: AsyncClient) -> None:
    """Second submit returns 409 Conflict."""
    payload = {"comments": [{"file": "x.py", "start_line": 1, "end_line": 1, "body": "note"}]}

    first = await client.post("/api/submit", json=payload)
    assert first.status_code == 200

    second = await client.post("/api/submit", json=payload)
    assert second.status_code == 409

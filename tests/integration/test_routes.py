"""API contract tests for the presentation layer."""

import asyncio
import json
from collections.abc import AsyncIterator
from importlib.metadata import version
from pathlib import Path

import pytest
from httpx import AsyncClient

from claude_review.domain.models import DiffFile, ReviewMode
from claude_review.services.text_files import read_text_files
from claude_review.services.transcript import read_transcript
from tests.helpers import (
    DIFF_ROUTE,
    EVENTS_ROUTE,
    WAIT_FOR_EVENT,
    ReviewFactory,
    added_line,
    context_line,
    diff_file,
    git,
    http_client,
    line_on_the_wire,
    removed_line,
    review_has_ended,
    thread_on_the_wire,
    uncommitted_changes,
    until_an_agent_waits,
)

REVIEW_TITLE = "test-repo: uncommitted changes"

A_NOTE = thread_on_the_wire(line_on_the_wire("x.py", 1), "fix this")


def _handler_change(path: str = "src/handler.ts") -> list[DiffFile]:
    """One file with a line replaced and one added, between two that stayed."""
    return [
        diff_file(
            path,
            [
                context_line(1, 1, "const x = 1;"),
                removed_line(2, "const y = 2;"),
                added_line(2, "const y = 3;"),
                added_line(3, "const z = 4;"),
                context_line(3, 4, "export { x };"),
            ],
        )
    ]


@pytest.fixture
async def client(reviews: ReviewFactory) -> AsyncIterator[AsyncClient]:
    async with http_client(reviews.app(_handler_change(), title=REVIEW_TITLE)) as agent:
        yield agent


async def _changed_lines(client: AsyncClient, *, ignore_whitespace: bool) -> list[str]:
    """What the diff shows as added or removed, with whitespace counted or not."""
    served = (await client.get(DIFF_ROUTE, params={"ignore_whitespace": ignore_whitespace})).json()
    return [
        line["content"]
        for changed in served["files"]
        for hunk in changed["hunks"]
        for line in hunk["lines"]
        if line["kind"] in ("add", "delete")
    ]


async def test_the_diff_serves_every_file_with_its_lines(client: AsyncClient) -> None:
    response = await client.get(DIFF_ROUTE)

    assert response.status_code == 200
    served = response.json()
    assert served["mode"] == "diff"
    [handler] = served["files"]
    assert (handler["path"], handler["status"]) == ("src/handler.ts", "modified")
    [hunk] = handler["hunks"]
    assert len(hunk["lines"]) == 5


async def test_each_line_says_which_side_it_is_on_and_where(client: AsyncClient) -> None:
    """A line kept, a line removed and a line added each carry the numbers of the sides they are on."""
    lines = (await client.get(DIFF_ROUTE)).json()["files"][0]["hunks"][0]["lines"]

    kept, removed, added = lines[:3]
    assert (kept["kind"], kept["old_number"], kept["new_number"]) == ("context", 1, 1)
    assert (removed["kind"], removed["old_number"], removed["new_number"]) == ("delete", 2, None)
    assert (added["kind"], added["old_number"], added["new_number"]) == ("add", None, 2)


async def test_a_sent_review_names_each_comment_by_its_file_and_lines(client: AsyncClient) -> None:
    response = await client.post(
        "/api/submit",
        json={
            "threads": [
                thread_on_the_wire(line_on_the_wire("src/handler.ts", 42), "Wrong null check", thread_id="comment-1"),
                thread_on_the_wire(line_on_the_wire("src/handler.ts", 67, 70), "Add max retry", thread_id="comment-2"),
            ],
            "end": True,
        },
    )

    assert response.status_code == 200
    sent = response.json()
    assert sent["comment_count"] == 2
    assert "### `src/handler.ts`:42" in sent["markdown"]
    assert "### `src/handler.ts`:67-70" in sent["markdown"]
    assert "Wrong null check" in sent["markdown"]
    assert "Add max retry" in sent["markdown"]


async def test_a_review_sent_with_nothing_in_it_says_nothing(client: AsyncClient) -> None:
    response = await client.post("/api/submit", json={"threads": [], "end": True})

    assert response.status_code == 200
    assert (response.json()["comment_count"], response.json()["markdown"]) == (0, "")


async def test_sending_the_review_ends_it(client: AsyncClient) -> None:
    await client.post("/api/submit", json={"threads": [A_NOTE], "end": True})

    assert await review_has_ended(client)


async def test_a_review_can_be_sent_only_once(client: AsyncClient) -> None:
    first = await client.post("/api/submit", json={"threads": [A_NOTE], "end": True})
    second = await client.post("/api/submit", json={"threads": [A_NOTE], "end": True})

    assert first.status_code == 200
    assert second.status_code == 409


async def test_an_agent_waiting_when_the_review_is_sent_is_handed_it_before_the_end(client: AsyncClient) -> None:
    """What was handed over outranks the review ending, or the last round would be dropped for it."""
    waiting = asyncio.ensure_future(client.get(EVENTS_ROUTE, params=WAIT_FOR_EVENT))
    await until_an_agent_waits(client)

    await client.post("/api/submit", json={"threads": [A_NOTE], "end": True})
    handed_over = (await waiting).json()

    assert handed_over["type"] == "round"
    assert "fix this" in handed_over["round"]["markdown"]
    assert await review_has_ended(client)


@pytest.mark.parametrize(
    "anchor",
    [
        line_on_the_wire("x.py", 10, 5),
        line_on_the_wire("x.py", 0, 1),
    ],
    ids=["ends-before-it-starts", "line-zero"],
)
async def test_a_comment_on_no_line_is_refused(client: AsyncClient, anchor: dict[str, object]) -> None:
    response = await client.post("/api/submit", json={"threads": [{**A_NOTE, "anchor": anchor}], "end": True})

    assert response.status_code == 422


async def test_a_comment_that_says_nothing_is_refused(client: AsyncClient) -> None:
    response = await client.post("/api/submit", json={"threads": [{**A_NOTE, "body": ""}], "end": True})

    assert response.status_code == 422


async def test_a_summary_alone_is_a_review(client: AsyncClient) -> None:
    """Wrong direction altogether is said in one paragraph, not on a line."""
    response = await client.post(
        "/api/submit", json={"threads": [], "body": "Wrong approach, reconsider the design.", "end": True}
    )

    assert response.status_code == 200
    assert response.json()["comment_count"] == 1
    assert "Wrong approach" in response.json()["markdown"]
    assert await review_has_ended(client)


async def test_the_summary_comes_before_the_comments(client: AsyncClient) -> None:
    response = await client.post(
        "/api/submit",
        json={"threads": [{**A_NOTE, "body": "Fix this"}], "body": "Generally good, one issue.", "end": True},
    )

    markdown = response.json()["markdown"]
    assert response.json()["comment_count"] == 2
    assert markdown.index("Generally good") < markdown.index("### `x.py`:1")


@pytest.fixture
def plan_file(tmp_path: Path) -> Path:
    """A real text file for files-mode integration tests."""
    plan = tmp_path / "plan.md"
    plan.write_text("# My Plan\n\nStep one\nStep two\n")
    return plan


@pytest.fixture
async def files_mode_client(plan_file: Path, reviews: ReviewFactory) -> AsyncIterator[AsyncClient]:
    """Client backed by a real text file, read as a files review reads it."""
    files = await read_text_files([plan_file], named_from=plan_file.parent)
    async with http_client(reviews.app(files, mode=ReviewMode.FILES)) as agent:
        yield agent


async def test_a_review_of_files_tells_the_page_it_is_one(files_mode_client: AsyncClient) -> None:
    """The page draws files differently from a diff, so it is told which it has."""
    response = await files_mode_client.get(DIFF_ROUTE)

    assert response.status_code == 200
    assert response.json()["mode"] == "files"


async def test_a_comment_on_a_line_of_a_file_reaches_the_agent_under_that_line(
    files_mode_client: AsyncClient,
) -> None:
    """Load a text file, comment on a specific line, send — and the review ends with it."""
    file_path = (await files_mode_client.get(DIFF_ROUTE)).json()["files"][0]["path"]

    # Line 3 is "Step one"
    response = await files_mode_client.post(
        "/api/submit",
        json={"threads": [thread_on_the_wire(line_on_the_wire(file_path, 3), "Needs more detail")], "end": True},
    )

    assert response.status_code == 200
    sent = response.json()
    assert sent["comment_count"] == 1
    assert f"### `{file_path}`:3" in sent["markdown"]
    assert "Needs more detail" in sent["markdown"]
    assert await review_has_ended(files_mode_client)


@pytest.fixture
def transcript_file(tmp_path: Path) -> Path:
    """A JSONL conversation file for transcript-mode integration tests."""
    conversation = tmp_path / "conversation.jsonl"
    entries = [
        {"type": "user", "message": {"role": "user", "content": "can you refactor the auth module?"}},
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "def authenticate(token):\n    return jwt.decode(token)"}],
            },
        },
    ]
    conversation.write_text("\n".join(json.dumps(entry) for entry in entries))
    return conversation


@pytest.fixture
async def transcript_mode_client(transcript_file: Path, reviews: ReviewFactory) -> AsyncIterator[AsyncClient]:
    """Client backed by a real transcript file, read as a conversation review reads it."""
    messages = await read_transcript(transcript_file)
    async with http_client(reviews.app(messages, mode=ReviewMode.TRANSCRIPT)) as agent:
        yield agent


async def test_a_review_of_a_conversation_serves_its_messages_newest_first(
    transcript_mode_client: AsyncClient,
) -> None:
    response = await transcript_mode_client.get(DIFF_ROUTE)

    assert response.status_code == 200
    served = response.json()
    assert served["mode"] == "transcript"
    newest, oldest = served["files"]
    assert "assistant" in newest["path"]
    assert "user" in oldest["path"]


async def test_a_comment_on_a_message_reaches_the_agent_with_the_message_quoted(
    transcript_mode_client: AsyncClient,
) -> None:
    """The agent may no longer hold the conversation, so the review quotes it."""
    served = (await transcript_mode_client.get(DIFF_ROUTE)).json()
    user_message = next(message for message in served["files"] if "user" in message["path"])

    response = await transcript_mode_client.post(
        "/api/submit",
        json={
            "threads": [thread_on_the_wire(line_on_the_wire(user_message["path"], 1), "Wrong approach")],
            "end": True,
        },
    )

    assert response.status_code == 200
    sent = response.json()
    assert sent["comment_count"] == 1
    assert "## Transcript Review" in sent["markdown"]
    assert "> can you refactor the auth module?" in sent["markdown"]
    assert "Wrong approach" in sent["markdown"]
    assert await review_has_ended(transcript_mode_client)


async def test_the_diff_says_what_is_under_review(client: AsyncClient) -> None:
    """The UI can name the thing being reviewed, not just list its files."""
    response = await client.get(DIFF_ROUTE)

    assert response.status_code == 200
    assert response.json()["title"] == REVIEW_TITLE


@pytest.fixture
async def repo_backed_client(tmp_path: Path, reviews: ReviewFactory) -> AsyncIterator[AsyncClient]:
    """A client whose server can read files, as diff mode's can."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("".join(f"line {line_number}\n" for line_number in range(1, 31)))
    async with http_client(reviews.app(_handler_change("src/app.py"), root=tmp_path, title=REVIEW_TITLE)) as agent:
        yield agent


async def test_file_window_serves_lines_the_diff_left_out(repo_backed_client: AsyncClient) -> None:
    """Context around a hunk can be widened without reloading the review."""
    response = await repo_backed_client.get("/api/file-window", params={"path": "src/app.py", "start": 4, "end": 6})

    assert response.status_code == 200
    assert response.json() == {"start": 4, "lines": ["line 4", "line 5", "line 6"], "total": 30}


async def test_file_window_refuses_to_leave_the_repository(repo_backed_client: AsyncClient) -> None:
    response = await repo_backed_client.get("/api/file-window", params={"path": "../outside.txt", "start": 1, "end": 1})

    assert response.status_code == 400


async def test_file_window_rejects_a_line_number_below_one(repo_backed_client: AsyncClient) -> None:
    response = await repo_backed_client.get("/api/file-window", params={"path": "src/app.py", "start": 0, "end": 3})

    assert response.status_code == 422


async def test_file_window_is_absent_without_a_repository(client: AsyncClient) -> None:
    """Files and transcript modes have no tree to widen context from."""
    response = await client.get("/api/file-window", params={"path": "a.py", "start": 1, "end": 2})

    assert response.status_code == 404


async def _committed_then_changed(repo: Path, committed: str, changed: str) -> list[DiffFile]:
    """The diff of app.py, committed as one text and then rewritten as another."""
    (repo / "app.py").write_text(committed)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "add")
    (repo / "app.py").write_text(changed)
    return await uncommitted_changes(repo)


async def test_ignoring_whitespace_leaves_the_real_change_visible(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """A reindented block should stop hiding the line that actually changed."""
    # Every line reindented, and one of them changed for real
    files = await _committed_then_changed(
        tmp_git_repo,
        "def f():\n  a = 1\n  b = 2\n  c = 3\n",
        "def f():\n    a = 1\n    b = 99\n    c = 3\n",
    )

    async with http_client(reviews.app(files, root=tmp_git_repo)) as client:
        plain = await _changed_lines(client, ignore_whitespace=False)
        ignored = await _changed_lines(client, ignore_whitespace=True)

    # Reindenting three lines buries the one that changed among six others
    assert len(plain) == 6
    assert ignored == ["  b = 2", "    b = 99"]


async def test_ignoring_whitespace_drops_a_reindent_only_change(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """A file whose only change is indentation disappears from the review."""
    files = await _committed_then_changed(tmp_git_repo, "def f():\n    return 1\n", "def f():\n        return 1\n")

    async with http_client(reviews.app(files, root=tmp_git_repo)) as client:
        plain = (await client.get(DIFF_ROUTE)).json()
        ignored = (await client.get(DIFF_ROUTE, params={"ignore_whitespace": True})).json()

    assert any(served["path"] == "app.py" for served in plain["files"])
    assert not any(served["path"] == "app.py" and served["hunks"] for served in ignored["files"])


async def test_ignoring_whitespace_can_be_turned_back_off(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """It is a way of looking at the diff, not a door that shuts behind you."""
    files = await _committed_then_changed(
        tmp_git_repo, "def f():\n  a = 1\n  b = 2\n", "def f():\n    a = 1\n    b = 99\n"
    )

    async with http_client(reviews.app(files, root=tmp_git_repo)) as client:
        full = (await client.get(DIFF_ROUTE)).json()
        ignored = await _changed_lines(client, ignore_whitespace=True)
        back = await _changed_lines(client, ignore_whitespace=False)

    assert len(ignored) < len(back)
    assert back == [
        line["content"]
        for served in full["files"]
        for hunk in served["hunks"]
        for line in hunk["lines"]
        if line["kind"] in ("add", "delete")
    ]


async def test_the_diff_says_which_release_serves_it(client: AsyncClient) -> None:
    """So the browser can tell a reader what changed since the release they last saw."""
    response = await client.get(DIFF_ROUTE)

    assert response.json()["release"] == version("claude-review")


async def test_file_window_widens_a_tracked_file_the_reviews_own_diff_does_not_hold(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """Read against another base, the diff on screen holds files the review's own does not; never an ignored one."""
    (tmp_git_repo / ".gitignore").write_text(".env\n")
    (tmp_git_repo / ".env").write_text("SECRET=hunter2\n")

    async with http_client(reviews.app([], root=tmp_git_repo)) as client:
        tracked = await client.get("/api/file-window", params={"path": "initial.txt", "start": 1, "end": 1})
        untracked = await client.get("/api/file-window", params={"path": ".env", "start": 1, "end": 1})

    assert tracked.json()["lines"] == ["initial content"]
    assert untracked.status_code == 404

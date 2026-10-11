"""API contract tests for the presentation layer."""

import asyncio
import json
from collections.abc import AsyncIterator
from http import HTTPMethod, HTTPStatus
from importlib.metadata import version
from pathlib import Path

import pytest
from httpx import AsyncClient

from claude_review.domain.models import DiffFile, ReviewMode
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.review_opening import ReviewOpening, open_diff
from claude_review.services.text_files import read_text_files
from claude_review.services.transcript import read_transcript
from tests.helpers import (
    DIFF_ROUTE,
    EVENTS_ROUTE,
    IMAGES_ROUTE,
    REVIEW_ROUTE,
    WAIT_FOR_EVENT,
    ReviewFactory,
    added_line,
    context_line,
    diff_file,
    git,
    http_client,
    line_on_the_wire,
    methods_allowed,
    opening_of,
    removed_line,
    repository_opening,
    review_has_ended,
    thread_on_the_wire,
    until_an_agent_waits,
    write_files,
)

REVIEW_TITLE = "test-repo: uncommitted changes"
# The file most of these reviews hold
HANDLER_FILE = "src/handler.ts"
# The file a review of a repository shows, how long it is, and the line its
# change replaces: far from the lines a test widens the context into
APP_FILE = "src/app.py"
APP_LINES = 30
CHANGED_APP_LINE = 20
CHANGED_APP_TEXT = "changed"
# The lines of it a test asks for that the diff leaves out
WIDENED_FROM = 4
WIDENED_TO = 6

# An image no review keeps: its path is reached, whatever it then answers
NO_SUCH_IMAGE = "never-pasted"

A_NOTE = thread_on_the_wire(line_on_the_wire("x.py", 1), "fix this")


def _handler_change() -> list[DiffFile]:
    """One file with a line replaced and one added, between two that stayed."""
    return [
        diff_file(
            HANDLER_FILE,
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
    async with http_client(reviews.app(opening_of(_handler_change(), title=REVIEW_TITLE))) as agent:
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

    assert response.status_code == HTTPStatus.OK
    [handler] = response.json()["files"]
    assert (handler["path"], handler["status"]) == (HANDLER_FILE, "modified")
    [hunk] = handler["hunks"]
    [changed] = _handler_change()
    assert [line["content"] for line in hunk["lines"]] == [line.content for line in changed.hunks[0].lines]


async def test_a_file_whose_name_no_thread_may_carry_is_served_as_read_only(reviews: ReviewFactory) -> None:
    """Git hands out names with a tab or an escape in them; a thread naming one would sink its whole round."""
    named_with_a_tab = diff_file("tab\there.py", [added_line(1, "x = 1")])

    async with http_client(reviews.app(opening_of([named_with_a_tab, *_handler_change()]))) as client:
        served = (await client.get(DIFF_ROUTE)).json()["files"]

    assert [(file["path"], file["commentable"]) for file in served] == [("tab\there.py", False), (HANDLER_FILE, True)]


async def test_each_line_says_which_side_it_is_on_and_where(client: AsyncClient) -> None:
    """A line kept, a line removed and a line added each carry the numbers of the sides they are on."""
    lines = (await client.get(DIFF_ROUTE)).json()["files"][0]["hunks"][0]["lines"]

    kept, removed, added = lines[:3]
    assert (kept["kind"], kept["old_number"], kept["new_number"]) == ("context", 1, 1)
    assert (removed["kind"], removed["old_number"], removed["new_number"]) == ("delete", 2, None)
    assert (added["kind"], added["old_number"], added["new_number"]) == ("add", None, 2)


async def test_a_sent_review_names_each_comment_by_its_file_and_lines(client: AsyncClient) -> None:
    threads = [
        thread_on_the_wire(line_on_the_wire(HANDLER_FILE, 42), "Wrong null check", thread_id="comment-1"),
        thread_on_the_wire(line_on_the_wire(HANDLER_FILE, 67, 70), "Add max retry", thread_id="comment-2"),
    ]

    response = await client.post("/api/submit", json={"threads": threads, "end": True})

    assert response.status_code == HTTPStatus.OK
    sent = response.json()
    assert sent["comment_count"] == len(threads)
    assert f"### `{HANDLER_FILE}`:42" in sent["markdown"]
    assert f"### `{HANDLER_FILE}`:67-70" in sent["markdown"]
    assert "Wrong null check" in sent["markdown"]
    assert "Add max retry" in sent["markdown"]


async def test_a_review_sent_with_nothing_in_it_says_nothing(client: AsyncClient) -> None:
    response = await client.post("/api/submit", json={"threads": [], "end": True})

    assert response.status_code == HTTPStatus.OK
    assert (response.json()["comment_count"], response.json()["markdown"]) == (0, "")


async def test_sending_the_review_ends_it(client: AsyncClient) -> None:
    await client.post("/api/submit", json={"threads": [A_NOTE], "end": True})

    assert await review_has_ended(client)


async def test_a_review_can_be_sent_only_once(client: AsyncClient) -> None:
    first = await client.post("/api/submit", json={"threads": [A_NOTE], "end": True})
    second = await client.post("/api/submit", json={"threads": [A_NOTE], "end": True})

    assert first.status_code == HTTPStatus.OK
    assert second.status_code == HTTPStatus.CONFLICT


async def test_an_agent_waiting_when_the_review_is_sent_is_handed_it_before_the_end(client: AsyncClient) -> None:
    """What was handed over outranks the review ending, or the last round would be dropped for it."""
    waiting = asyncio.ensure_future(client.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT))
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

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_a_comment_that_says_nothing_is_refused(client: AsyncClient) -> None:
    response = await client.post("/api/submit", json={"threads": [{**A_NOTE, "body": ""}], "end": True})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_a_summary_alone_is_a_review(client: AsyncClient) -> None:
    """Wrong direction altogether is said in one paragraph, not on a line."""
    response = await client.post(
        "/api/submit", json={"threads": [], "body": "Wrong approach, reconsider the design.", "end": True}
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["comment_count"] == 1
    assert "Wrong approach" in response.json()["markdown"]
    assert await review_has_ended(client)


async def test_the_summary_comes_before_the_comments(client: AsyncClient) -> None:
    threads = [{**A_NOTE, "body": "Fix this"}]

    response = await client.post(
        "/api/submit", json={"threads": threads, "body": "Generally good, one issue.", "end": True}
    )

    markdown = response.json()["markdown"]
    # The summary counts as one
    assert response.json()["comment_count"] == len(threads) + 1
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
    async with http_client(reviews.app(opening_of(files, mode=ReviewMode.FILES))) as agent:
        yield agent


async def test_a_review_of_files_tells_the_page_it_is_one(files_mode_client: AsyncClient) -> None:
    """The page draws files differently from a diff, so it is told which it has."""
    response = await files_mode_client.get(REVIEW_ROUTE)

    assert response.status_code == HTTPStatus.OK
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

    assert response.status_code == HTTPStatus.OK
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
    async with http_client(reviews.app(opening_of(messages, mode=ReviewMode.TRANSCRIPT))) as agent:
        yield agent


async def test_a_review_of_a_conversation_serves_its_messages_newest_first(
    transcript_mode_client: AsyncClient,
) -> None:
    response = await transcript_mode_client.get(DIFF_ROUTE)

    assert response.status_code == HTTPStatus.OK
    assert (await transcript_mode_client.get(REVIEW_ROUTE)).json()["mode"] == "transcript"
    newest, oldest = response.json()["files"]
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

    assert response.status_code == HTTPStatus.OK
    sent = response.json()
    assert sent["comment_count"] == 1
    assert "## Transcript Review" in sent["markdown"]
    assert "> can you refactor the auth module?" in sent["markdown"]
    assert "Wrong approach" in sent["markdown"]
    assert await review_has_ended(transcript_mode_client)


async def test_the_review_says_what_is_under_review(client: AsyncClient) -> None:
    """The UI can name the thing being reviewed, not just list its files."""
    response = await client.get(REVIEW_ROUTE)

    assert response.status_code == HTTPStatus.OK
    assert response.json()["title"] == REVIEW_TITLE


async def _identity_of(reviews: ReviewFactory, opening: ReviewOpening) -> str:
    """The name a review gives itself to the page that opens it."""
    async with http_client(reviews.app(opening)) as client:
        return (await client.get(REVIEW_ROUTE)).json()["identity"]


def _changed_repository(root: Path) -> Path:
    """A repository with one commit and a change on top of it."""
    root.mkdir(parents=True)
    git(root, "init", "-b", "main")
    write_files(root, {"a.py": "x = 1\n"})
    git(root, "add", ".")
    git(root, "-c", "user.name=Test", "-c", "user.email=test@test.com", "commit", "-m", "initial")
    write_files(root, {"a.py": "x = 2\n"})
    return root


async def test_the_review_names_itself_the_same_whenever_it_is_opened_and_apart_from_any_other(
    tmp_path: Path, reviews: ReviewFactory
) -> None:
    """A page keeps the reader's unsent work under this name: the same review opened again finds it, another never does.

    Two repositories of one name have one title, and land on one port when
    the reader names it: the name must tell them apart all the same.
    """
    one = _changed_repository(tmp_path / "one" / "app")
    namesake = _changed_repository(tmp_path / "two" / "app")

    first = await _identity_of(reviews, await repository_opening(one))
    again = await _identity_of(reviews, await repository_opening(one))
    against_head = await _identity_of(reviews, await open_diff(one, "HEAD", GitRepository(objects=None)))
    of_the_namesake = await _identity_of(reviews, await repository_opening(namesake))

    assert first == again
    assert first not in {against_head, of_the_namesake}
    assert str(one) not in first, "the name says nothing of what it is made of"


def _app_line(number: int) -> str:
    """What a line of the app says, by its number, until the change."""
    return f"line {number}"


@pytest.fixture
async def repo_backed_client(tmp_git_repo: Path, reviews: ReviewFactory) -> AsyncIterator[AsyncClient]:
    """A client of a review of a repository, whose server can read what the diff leaves out."""
    lines = [f"{_app_line(number)}\n" for number in range(1, APP_LINES + 1)]
    write_files(tmp_git_repo, {APP_FILE: "".join(lines)})
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "app")
    lines[CHANGED_APP_LINE - 1] = f"{CHANGED_APP_TEXT}\n"
    write_files(tmp_git_repo, {APP_FILE: "".join(lines)})
    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as agent:
        yield agent


async def test_file_window_serves_lines_the_diff_left_out(repo_backed_client: AsyncClient) -> None:
    """Context around a hunk can be widened without reloading the review."""
    response = await repo_backed_client.get(
        "/api/file-window", params={"path": APP_FILE, "start": WIDENED_FROM, "end": WIDENED_TO}
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "start": WIDENED_FROM,
        "lines": [_app_line(number) for number in range(WIDENED_FROM, WIDENED_TO + 1)],
        "total": APP_LINES,
    }


async def test_file_window_refuses_to_leave_the_repository(repo_backed_client: AsyncClient) -> None:
    response = await repo_backed_client.get("/api/file-window", params={"path": "../outside.txt", "start": 1, "end": 1})

    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_file_window_rejects_a_line_number_below_one(repo_backed_client: AsyncClient) -> None:
    response = await repo_backed_client.get("/api/file-window", params={"path": APP_FILE, "start": 0, "end": 3})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_file_window_is_absent_without_a_repository(client: AsyncClient) -> None:
    """A review of files read once has no tree to widen context from."""
    response = await client.get("/api/file-window", params={"path": "a.py", "start": 1, "end": 2})

    assert response.status_code == HTTPStatus.NOT_FOUND


async def _committed_then_changed(repo: Path, committed: str, changed: str) -> ReviewOpening:
    """A review of app.py, committed as one text and then rewritten as another, opened as the command line opens it."""
    (repo / "app.py").write_text(committed)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "add")
    (repo / "app.py").write_text(changed)
    return await repository_opening(repo)


async def test_ignoring_whitespace_leaves_the_real_change_visible(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """A reindented block should stop hiding the line that actually changed."""
    # Every line reindented, and one of them changed for real
    opening = await _committed_then_changed(
        tmp_git_repo,
        "def f():\n  a = 1\n  b = 2\n  c = 3\n",
        "def f():\n    a = 1\n    b = 99\n    c = 3\n",
    )

    async with http_client(reviews.app(opening)) as client:
        plain = await _changed_lines(client, ignore_whitespace=False)
        ignored = await _changed_lines(client, ignore_whitespace=True)

    # Reindenting three lines buries the one that changed among six others
    assert plain == ["  a = 1", "  b = 2", "  c = 3", "    a = 1", "    b = 99", "    c = 3"]
    assert ignored == ["  b = 2", "    b = 99"]


async def test_ignoring_whitespace_drops_a_reindent_only_change(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """A file whose only change is indentation disappears from the review."""
    opening = await _committed_then_changed(tmp_git_repo, "def f():\n    return 1\n", "def f():\n        return 1\n")

    async with http_client(reviews.app(opening)) as client:
        plain = (await client.get(DIFF_ROUTE)).json()
        ignored = (await client.get(DIFF_ROUTE, params={"ignore_whitespace": True})).json()

    assert any(served["path"] == "app.py" for served in plain["files"])
    assert not any(served["path"] == "app.py" and served["hunks"] for served in ignored["files"])


async def test_ignoring_whitespace_can_be_turned_back_off(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """It is a way of looking at the diff, not a door that shuts behind you."""
    opening = await _committed_then_changed(
        tmp_git_repo, "def f():\n  a = 1\n  b = 2\n", "def f():\n    a = 1\n    b = 99\n"
    )

    async with http_client(reviews.app(opening)) as client:
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


async def test_a_renamed_file_is_served_with_where_it_was(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """Without it the page shows a new file, and the reader cannot tell a rename from a rewrite."""
    (tmp_git_repo / "before.py").write_text("moved, not changed\n")
    git(tmp_git_repo, "add", ".")
    git(tmp_git_repo, "commit", "-m", "add the file")
    git(tmp_git_repo, "mv", "before.py", "after.py")

    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        [served] = (await client.get(DIFF_ROUTE)).json()["files"]

    assert (served["path"], served["old_path"]) == ("after.py", "before.py")


async def test_the_review_says_which_release_serves_it(client: AsyncClient) -> None:
    """So the browser can tell a reader what changed since the release they last saw."""
    response = await client.get(REVIEW_ROUTE)

    assert response.json()["release"] == version("claude-review")


async def test_file_window_widens_a_tracked_file_the_reviews_own_diff_does_not_hold(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """Read against another base, the diff on screen holds files the review's own does not; never an ignored one."""
    (tmp_git_repo / ".gitignore").write_text(".env\n")
    (tmp_git_repo / ".env").write_text("SECRET=hunter2\n")

    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        tracked = await client.get("/api/file-window", params={"path": "initial.txt", "start": 1, "end": 1})
        untracked = await client.get("/api/file-window", params={"path": ".env", "start": 1, "end": 1})

    assert tracked.json()["lines"] == ["initial content"]
    assert untracked.status_code == HTTPStatus.NOT_FOUND


async def test_a_method_a_path_does_not_take_is_refused_naming_every_method_it_does(client: AsyncClient) -> None:
    """One route reads an image and another discards it: the refusal names both, not only the first one found."""
    response = await client.put(f"{IMAGES_ROUTE}/{NO_SUCH_IMAGE}")

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert methods_allowed(response) == {HTTPMethod.GET, HTTPMethod.DELETE}

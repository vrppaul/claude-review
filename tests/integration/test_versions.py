"""Choosing what the working tree is compared against.

The right-hand side of a review's diff is always the working tree, so the
base is the only thing there is to choose. A narrower one — the tree as some
earlier round read it — answers "what has changed since I last looked",
which is the question a round leaves behind.
"""

import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from claude_review.domain.models import ReviewMode
from claude_review.presentation.app import create_app
from claude_review.presentation.state import ServerState
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.tree_watcher_service import TreeWatcherService
from claude_review.services.version_service import VersionService
from tests.helpers import git

LOCAL_ORIGIN = "http://127.0.0.1:8000"
LOCAL_HEADERS = {"Origin": LOCAL_ORIGIN, "Host": "127.0.0.1:8000"}


@pytest.fixture
def state() -> ServerState:
    return ServerState(shutdown_event=asyncio.Event())


@pytest.fixture
def store(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("review-objects")


async def _mark(state: ServerState, root: Path, store: Path, round_number: int) -> None:
    """Write down the tree as it stands, the way opening a review does."""
    taken = await VersionService(git_repository=GitRepository(objects=store)).take(root, round_number=round_number)
    assert taken is not None
    state.snapshots.append(taken)


def _client(state: ServerState, root: Path, store: Path, base: str | None = None) -> AsyncClient:
    app = create_app(diff_files=[], state=state, mode=ReviewMode.DIFF, root=root, base=base, objects=store)
    return AsyncClient(transport=ASGITransport(app=app), base_url=LOCAL_ORIGIN)


async def test_the_review_and_its_rounds_are_on_offer(tmp_git_repo: Path, state: ServerState, store: Path) -> None:
    """What this review opened against, and every round that left a mark."""
    (tmp_git_repo / "work.py").write_text("first\n")
    await _mark(state, tmp_git_repo, store, round_number=1)
    (tmp_git_repo / "work.py").write_text("second\n")
    await _mark(state, tmp_git_repo, store, round_number=2)

    async with _client(state, tmp_git_repo, store) as client:
        offered = (await client.get("/api/versions", headers=LOCAL_HEADERS)).json()["versions"]

    assert [v["key"] for v in offered if v["kind"] != "ref"] == ["review", "round:1"]
    assert [v["phrase"] for v in offered if v["kind"] != "ref"] == [
        "uncommitted changes",
        "changes since round 1",
    ]


async def test_the_review_says_how_many_files_a_base_would_show(
    tmp_git_repo: Path, state: ServerState, store: Path
) -> None:
    """The count is the reason to pick one base over another."""
    (tmp_git_repo / "before.py").write_text("was here\n")
    await _mark(state, tmp_git_repo, store, round_number=1)
    (tmp_git_repo / "after.py").write_text("came later\n")
    await _mark(state, tmp_git_repo, store, round_number=2)

    async with _client(state, tmp_git_repo, store) as client:
        offered = (await client.get("/api/versions", headers=LOCAL_HEADERS)).json()["versions"]

    by_key = {v["key"]: v for v in offered}
    assert by_key["review"]["changed"] == 2, "both files are new since the review opened"
    assert by_key["round:1"]["changed"] == 1, "only one of them arrived after round 1"


async def test_branches_and_tags_are_on_offer(tmp_git_repo: Path, state: ServerState, store: Path) -> None:
    """The base a review opened with is not the only one worth reading against."""
    git(tmp_git_repo, "branch", "earlier")
    git(tmp_git_repo, "tag", "v0.1.0")

    async with _client(state, tmp_git_repo, store) as client:
        offered = (await client.get("/api/versions", headers=LOCAL_HEADERS)).json()["versions"]

    refs = [v["label"] for v in offered if v["kind"] == "ref"]
    assert "earlier" in refs
    assert "v0.1.0" in refs


async def test_the_diff_can_be_taken_against_a_round(tmp_git_repo: Path, state: ServerState, store: Path) -> None:
    """What the agent did about round 1, with nothing else in the way."""
    (tmp_git_repo / "answered.py").write_text("as it was\n")
    (tmp_git_repo / "elsewhere.py").write_text("untouched since\n")
    await _mark(state, tmp_git_repo, store, round_number=1)
    (tmp_git_repo / "answered.py").write_text("as the round asked\n")

    async with _client(state, tmp_git_repo, store) as client:
        narrowed = (await client.get("/api/diff?base=round:1", headers=LOCAL_HEADERS)).json()

    assert [f["path"] for f in narrowed["files"]] == ["answered.py"]


async def test_a_base_nobody_offered_is_refused(tmp_git_repo: Path, state: ServerState, store: Path) -> None:
    """What reaches git as a revision is never whatever arrived in the query."""
    async with _client(state, tmp_git_repo, store) as client:
        made_up = await client.get("/api/diff?base=ref:--output=/tmp/x", headers=LOCAL_HEADERS)
        no_such_round = await client.get("/api/diff?base=round:9", headers=LOCAL_HEADERS)

    assert made_up.status_code == 400
    assert no_such_round.status_code == 400


async def test_the_review_keeps_its_own_diff_whatever_is_being_looked_at(
    tmp_git_repo: Path, state: ServerState, store: Path
) -> None:
    """A base is a way of looking, not a change to what is under review."""
    (tmp_git_repo / "from_the_start.py").write_text("here all along\n")
    await _mark(state, tmp_git_repo, store, round_number=1)
    (tmp_git_repo / "later.py").write_text("came after\n")

    async with _client(state, tmp_git_repo, store) as client:
        await client.post("/api/round", json={}, headers=LOCAL_HEADERS)
        narrowed = (await client.get("/api/diff?base=round:1", headers=LOCAL_HEADERS)).json()
        whole = (await client.get("/api/diff", headers=LOCAL_HEADERS)).json()

    assert [f["path"] for f in narrowed["files"]] == ["later.py"]
    assert sorted(f["path"] for f in whole["files"]) == ["from_the_start.py", "later.py"]


async def test_a_review_without_a_repository_offers_no_bases(state: ServerState) -> None:
    """Files and transcripts are not compared against anything."""
    app = create_app(diff_files=[], state=state, mode=ReviewMode.FILES)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=LOCAL_ORIGIN) as client:
        offered = (await client.get("/api/versions", headers=LOCAL_HEADERS)).json()

    assert offered["versions"] == []


async def test_a_round_nothing_has_happened_since_is_not_offered(
    tmp_git_repo: Path, state: ServerState, store: Path
) -> None:
    """It would open an empty screen, and leave the reader wondering what they broke."""
    (tmp_git_repo / "work.py").write_text("done\n")
    await _mark(state, tmp_git_repo, store, round_number=1)

    async with _client(state, tmp_git_repo, store) as client:
        offered = (await client.get("/api/versions", headers=LOCAL_HEADERS)).json()["versions"]

    assert [v["key"] for v in offered if v["kind"] == "round"] == []


async def test_an_annotated_tag_is_offered_like_any_other(tmp_git_repo: Path, state: ServerState, store: Path) -> None:
    """A tag object has a tagger and no committer, and asking for the wrong one drops it."""
    git(tmp_git_repo, "tag", "-a", "v2.0.0", "-m", "release")

    async with _client(state, tmp_git_repo, store) as client:
        offered = (await client.get("/api/versions", headers=LOCAL_HEADERS)).json()["versions"]

    assert "v2.0.0" in [v["label"] for v in offered if v["kind"] == "ref"]


async def test_a_ref_whose_name_begins_with_a_dash_is_never_a_base(
    tmp_git_repo: Path, state: ServerState, store: Path
) -> None:
    """Git allows the name, and `git diff` would read it as an option."""
    git(tmp_git_repo, "update-ref", "refs/heads/--output=/tmp/claude-review-should-not-exist", "HEAD")

    async with _client(state, tmp_git_repo, store) as client:
        offered = (await client.get("/api/versions", headers=LOCAL_HEADERS)).json()["versions"]
        asked = await client.get(
            "/api/diff?base=ref:--output=/tmp/claude-review-should-not-exist", headers=LOCAL_HEADERS
        )

    assert [v for v in offered if v["label"].startswith("-")] == []
    assert asked.status_code == 400
    # Off the loop: touching the filesystem from an async test blocks it, and
    # what this asserts is precisely that nothing touched the filesystem
    assert not await asyncio.to_thread(Path("/tmp/claude-review-should-not-exist").exists)


async def test_a_repository_with_nothing_committed_still_offers_its_bases(
    tmp_path: Path, state: ServerState, store: Path
) -> None:
    """No HEAD means no counts; it does not mean no menu."""
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    git(fresh, "init", "-b", "main")
    (fresh / "started.py").write_text("nothing committed yet\n")

    async with _client(state, fresh, store) as client:
        offered = (await client.get("/api/versions", headers=LOCAL_HEADERS)).json()["versions"]

    assert [v["key"] for v in offered] == ["review"]
    assert offered[0]["changed"] is None, "a count that cannot be taken is not a count of zero"


async def test_the_diff_says_how_far_the_tree_has_moved_since_it_was_taken(
    tmp_git_repo: Path, state: ServerState, store: Path
) -> None:
    """A review reloaded while the tree was moving heard the push and lost it."""
    state.tree = await TreeWatcherService(git_repository=GitRepository()).read(tmp_git_repo)
    (tmp_git_repo / "moved_after.py").write_text("written while the review was open\n")

    async with _client(state, tmp_git_repo, store) as client:
        served = (await client.get("/api/diff", headers=LOCAL_HEADERS)).json()

    assert served["moved"] == 1

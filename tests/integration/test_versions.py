"""Choosing what the working tree is compared against.

The right-hand side of a review's diff is always the working tree, so the
base is the only thing there is to choose. A narrower one — the tree as some
earlier round read it — answers "what has changed since I last looked",
which is the question a round leaves behind.
"""

import asyncio
import time
from pathlib import Path

import pytest
from httpx import AsyncClient

from claude_review.domain.models import ReviewMode
from tests.helpers import DIFF_ROUTE, LOCAL_HEADERS, FixedClock, ReviewFactory, git, http_client, uncommitted_changes

VERSIONS_ROUTE = "/api/versions"

# A moment on the review's clock, in epoch milliseconds
A_MOMENT = 1_791_000_000_000
MILLISECONDS_PER_SECOND = 1000
# How far a commit made during the test may be from now, generously
AN_HOUR_IN_MILLISECONDS = 60 * 60 * MILLISECONDS_PER_SECOND


async def _mark(client: AsyncClient) -> None:
    """Take the diff again, which writes down the tree as it stands for the round being written."""
    await client.post("/api/retake", json={}, headers=LOCAL_HEADERS)


async def _begin_next_round(client: AsyncClient) -> None:
    await client.post("/api/submit", json={"threads": [], "end": False}, headers=LOCAL_HEADERS)


async def _offered(client: AsyncClient) -> list[dict]:
    return (await client.get(VERSIONS_ROUTE, headers=LOCAL_HEADERS)).json()["versions"]


async def test_the_review_and_its_rounds_are_on_offer(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """What this review opened against, and every round that left a mark."""
    async with http_client(reviews.app([], root=tmp_git_repo)) as client:
        (tmp_git_repo / "work.py").write_text("first\n")
        await _mark(client)
        await _begin_next_round(client)
        (tmp_git_repo / "work.py").write_text("second\n")
        await _mark(client)

        offered = [version for version in await _offered(client) if version["kind"] != "ref"]

    assert [version["key"] for version in offered] == ["review", "round:1"]
    assert [version["phrase"] for version in offered] == ["uncommitted changes", "changes since round 1"]


async def test_a_round_is_dated_when_it_was_read(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    async with http_client(reviews.app([], root=tmp_git_repo, clock=FixedClock(A_MOMENT))) as client:
        (tmp_git_repo / "work.py").write_text("first\n")
        await _mark(client)
        await _begin_next_round(client)
        (tmp_git_repo / "work.py").write_text("second\n")
        await _mark(client)

        by_key = {version["key"]: version for version in await _offered(client)}

    assert by_key["round:1"]["at"] == A_MOMENT


async def test_a_branch_is_dated_in_the_same_unit_as_everything_else(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """Epoch milliseconds, like every other time the review says; git says seconds."""
    git(tmp_git_repo, "branch", "earlier")
    async with http_client(reviews.app([], root=tmp_git_repo)) as client:
        by_label = {version["label"]: version for version in await _offered(client) if version["kind"] == "ref"}

    assert abs(by_label["earlier"]["at"] - time.time() * MILLISECONDS_PER_SECOND) < AN_HOUR_IN_MILLISECONDS


async def test_the_review_says_how_many_files_a_base_would_show(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """The count is the reason to pick one base over another."""
    (tmp_git_repo / "before.py").write_text("was here\n")
    async with http_client(reviews.app([], root=tmp_git_repo)) as client:
        await _begin_next_round(client)
        (tmp_git_repo / "after.py").write_text("came later\n")
        await _mark(client)

        by_key = {version["key"]: version for version in await _offered(client)}

    assert by_key["review"]["changed"] == 2, "both files are uncommitted"
    assert by_key["round:1"]["changed"] == 1, "only one of them arrived after round 1 began"


async def test_branches_and_tags_are_on_offer(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """The base a review opened with is not the only one worth reading against."""
    git(tmp_git_repo, "branch", "earlier")
    git(tmp_git_repo, "tag", "v0.1.0")

    async with http_client(reviews.app([], root=tmp_git_repo)) as client:
        refs = [version["label"] for version in await _offered(client) if version["kind"] == "ref"]

    assert "earlier" in refs
    assert "v0.1.0" in refs


async def test_the_diff_can_be_taken_against_a_round(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """What the agent did about round 1, with nothing else in the way."""
    (tmp_git_repo / "answered.py").write_text("as it was\n")
    (tmp_git_repo / "elsewhere.py").write_text("untouched since\n")

    async with http_client(reviews.app([], root=tmp_git_repo)) as client:
        await _mark(client)
        (tmp_git_repo / "answered.py").write_text("as the round asked\n")

        narrowed = (await client.get(DIFF_ROUTE, params={"base": "round:1"}, headers=LOCAL_HEADERS)).json()

    assert [served["path"] for served in narrowed["files"]] == ["answered.py"]


@pytest.mark.parametrize(
    "base",
    ["ref:--output=/tmp/x", "round:9", "round:0", "round:abc", "ref:", "ref:-x", "branch:main"],
    ids=["option-as-ref", "round-never-sent", "round-zero", "round-not-a-number", "empty-ref", "dash-ref", "no-kind"],
)
async def test_a_base_nobody_offered_is_refused(tmp_git_repo: Path, reviews: ReviewFactory, base: str) -> None:
    """What reaches git as a revision is never whatever arrived in the query."""
    async with http_client(reviews.app([], root=tmp_git_repo)) as client:
        await _mark(client)

        asked = await client.get(DIFF_ROUTE, params={"base": base}, headers=LOCAL_HEADERS)

    assert asked.status_code == 400


async def test_the_review_keeps_its_own_diff_whatever_is_being_looked_at(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """A base is a way of looking, not a change to what is under review."""
    (tmp_git_repo / "from_the_start.py").write_text("here all along\n")

    async with http_client(reviews.app([], root=tmp_git_repo)) as client:
        await _mark(client)
        (tmp_git_repo / "later.py").write_text("came after\n")
        await _mark(client)

        narrowed = (await client.get(DIFF_ROUTE, params={"base": "round:1"}, headers=LOCAL_HEADERS)).json()
        whole = (await client.get(DIFF_ROUTE, headers=LOCAL_HEADERS)).json()

    assert [served["path"] for served in narrowed["files"]] == ["later.py"]
    assert sorted(served["path"] for served in whole["files"]) == ["from_the_start.py", "later.py"]


async def test_a_review_without_a_repository_offers_no_bases(reviews: ReviewFactory) -> None:
    """Files and transcripts are not compared against anything."""
    async with http_client(reviews.app([], mode=ReviewMode.FILES)) as client:
        assert await _offered(client) == []


async def test_a_round_nothing_has_happened_since_is_not_offered(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """It would open an empty screen, and leave the reader wondering what they broke."""
    (tmp_git_repo / "work.py").write_text("done\n")

    async with http_client(reviews.app([], root=tmp_git_repo)) as client:
        await _mark(client)
        offered = await _offered(client)

    assert [version["key"] for version in offered if version["kind"] == "round"] == []


async def test_an_annotated_tag_is_offered_like_any_other(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """A tag object has a tagger and no committer, and asking for the wrong one drops it."""
    git(tmp_git_repo, "tag", "-a", "v2.0.0", "-m", "release")

    async with http_client(reviews.app([], root=tmp_git_repo)) as client:
        offered = await _offered(client)

    assert "v2.0.0" in [version["label"] for version in offered if version["kind"] == "ref"]


async def test_a_ref_whose_name_begins_with_a_dash_is_never_a_base(
    tmp_git_repo: Path, tmp_path_factory: pytest.TempPathFactory, reviews: ReviewFactory
) -> None:
    """Git allows the name, and `git diff` would read it as an option."""
    target = tmp_path_factory.mktemp("outside") / "written-by-git"
    git(tmp_git_repo, "update-ref", f"refs/heads/--output={target}", "HEAD")

    async with http_client(reviews.app([], root=tmp_git_repo)) as client:
        offered = await _offered(client)
        asked = await client.get(DIFF_ROUTE, params={"base": f"ref:--output={target}"}, headers=LOCAL_HEADERS)

    assert [version for version in offered if version["label"].startswith("-")] == []
    assert asked.status_code == 400
    # Off the loop: touching the filesystem from an async test blocks it, and
    # what this asserts is precisely that nothing touched the filesystem
    assert not await asyncio.to_thread(target.exists)


async def test_a_repository_with_nothing_committed_still_offers_its_bases(
    tmp_path: Path, reviews: ReviewFactory
) -> None:
    """No HEAD means no counts; it does not mean no menu."""
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    git(fresh, "init", "-b", "main")
    (fresh / "started.py").write_text("nothing committed yet\n")

    async with http_client(reviews.app([], root=fresh)) as client:
        offered = await _offered(client)

    assert [version["key"] for version in offered] == ["review"]
    assert offered[0]["changed"] is None, "a count that cannot be taken is not a count of zero"


async def test_the_diff_says_how_far_the_tree_has_moved_since_it_was_taken(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """A review reloaded while the tree was moving heard the push and lost it."""
    async with http_client(reviews.app([], root=tmp_git_repo)) as client:
        await _mark(client)
        (tmp_git_repo / "moved_after.py").write_text("written while the review was open\n")

        served = (await client.get(DIFF_ROUTE, headers=LOCAL_HEADERS)).json()

    assert served["moved"] == 1


async def test_a_review_opens_on_the_tree_its_first_round_is_marked_at(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """Whatever changed between reading the diff and serving it is on screen, so "since round 1" counts from there."""
    read_before = await uncommitted_changes(tmp_git_repo)
    (tmp_git_repo / "written_in_between.py").write_text("saved while the review was starting\n")

    async with http_client(reviews.app(read_before, root=tmp_git_repo)) as client:
        served = (await client.get(DIFF_ROUTE, headers=LOCAL_HEADERS)).json()
        by_key = {version["key"]: version for version in await _offered(client)}

    assert [file["path"] for file in served["files"]] == ["written_in_between.py"]
    assert "round:1" not in by_key, "nothing has changed since the tree round 1 began at"

"""Choosing what the working tree is compared against.

The right-hand side of a review's diff is always the working tree, so the
base is the only thing there is to choose. A narrower one — the tree as some
earlier round read it — answers "what has changed since I last looked",
which is the question a round leaves behind.
"""

import asyncio
import time
from http import HTTPStatus
from pathlib import Path

import pytest
from httpx import AsyncClient

from claude_review.domain.models import ReviewMode
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.review_opening import open_diff
from tests.helpers import (
    DIFF_ROUTE,
    LOCAL_HEADERS,
    FixedClock,
    ReviewFactory,
    git,
    http_client,
    line_json,
    opening_of,
    repository_opening,
)

VERSIONS_ROUTE = "/api/versions"
FOLLOW_ROUTE = "/api/anchors/follow"
RETAKE_ROUTE = "/api/retake"

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
    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        (tmp_git_repo / "work.py").write_text("first\n")
        await _mark(client)
        await _begin_next_round(client)
        (tmp_git_repo / "work.py").write_text("second\n")
        await _mark(client)

        offered = [version for version in await _offered(client) if version["kind"] != "ref"]

    assert [version["key"] for version in offered] == ["review", "round:1"]
    assert [version["phrase"] for version in offered] == ["uncommitted changes", "changes since round 1"]


async def test_a_round_is_dated_when_it_was_read(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    async with http_client(reviews.app(await repository_opening(tmp_git_repo), clock=FixedClock(A_MOMENT))) as client:
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
    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        by_label = {version["label"]: version for version in await _offered(client) if version["kind"] == "ref"}

    assert abs(by_label["earlier"]["at"] - time.time() * MILLISECONDS_PER_SECOND) < AN_HOUR_IN_MILLISECONDS


async def test_the_review_says_how_many_files_a_base_would_show(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """The count is the reason to pick one base over another."""
    before, after = "before.py", "after.py"
    (tmp_git_repo / before).write_text("was here\n")
    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        await _begin_next_round(client)
        (tmp_git_repo / after).write_text("came later\n")
        await _mark(client)

        by_key = {version["key"]: version for version in await _offered(client)}

    assert by_key["review"]["changed"] == len((before, after)), "both files are uncommitted"
    assert by_key["round:1"]["changed"] == 1, "only one of them arrived after round 1 began"


async def test_branches_and_tags_are_on_offer(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """The base a review opened with is not the only one worth reading against."""
    git(tmp_git_repo, "branch", "earlier")
    git(tmp_git_repo, "tag", "v0.1.0")

    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        refs = [version["label"] for version in await _offered(client) if version["kind"] == "ref"]

    assert "earlier" in refs
    assert "v0.1.0" in refs


async def test_the_diff_can_be_taken_against_a_round(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """What the agent did about round 1, with nothing else in the way."""
    (tmp_git_repo / "answered.py").write_text("as it was\n")
    (tmp_git_repo / "elsewhere.py").write_text("untouched since\n")

    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
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
    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        await _mark(client)

        asked = await client.get(DIFF_ROUTE, params={"base": base}, headers=LOCAL_HEADERS)

    assert asked.status_code == HTTPStatus.BAD_REQUEST


async def test_the_review_keeps_its_own_diff_whatever_is_being_looked_at(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """A base is a way of looking, not a change to what is under review."""
    (tmp_git_repo / "from_the_start.py").write_text("here all along\n")

    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        await _mark(client)
        (tmp_git_repo / "later.py").write_text("came after\n")
        await _mark(client)

        narrowed = (await client.get(DIFF_ROUTE, params={"base": "round:1"}, headers=LOCAL_HEADERS)).json()
        whole = (await client.get(DIFF_ROUTE, headers=LOCAL_HEADERS)).json()

    assert [served["path"] for served in narrowed["files"]] == ["later.py"]
    assert sorted(served["path"] for served in whole["files"]) == ["from_the_start.py", "later.py"]


async def test_the_diff_names_the_base_it_was_taken_against_and_whether_it_is_narrower_than_the_reviews(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """The page asks by the key, says the words, and draws every thread only while the review's own is in force."""
    (tmp_git_repo / "answered.py").write_text("as it was\n")

    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        await _mark(client)
        (tmp_git_repo / "answered.py").write_text("as the round asked\n")

        narrowed = (await client.get(DIFF_ROUTE, params={"base": "round:1"}, headers=LOCAL_HEADERS)).json()
        whole = (await client.get(DIFF_ROUTE, headers=LOCAL_HEADERS)).json()

    assert narrowed["base"] == {"key": "round:1", "phrase": "changes since round 1", "narrowed": True}
    assert whole["base"] == {"key": "review", "phrase": "uncommitted changes", "narrowed": False}


async def test_a_review_without_a_repository_offers_no_bases(reviews: ReviewFactory) -> None:
    """Files and transcripts are not compared against anything."""
    async with http_client(reviews.app(opening_of([], mode=ReviewMode.FILES))) as client:
        assert await _offered(client) == []
        assert (await client.get(DIFF_ROUTE, headers=LOCAL_HEADERS)).json()["base"] is None


async def test_a_round_nothing_has_happened_since_is_not_offered(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """It would open an empty screen, and leave the reader wondering what they broke."""
    (tmp_git_repo / "work.py").write_text("done\n")

    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        await _mark(client)
        offered = await _offered(client)

    assert [version["key"] for version in offered if version["kind"] == "round"] == []


async def test_an_annotated_tag_is_offered_like_any_other(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """A tag object has a tagger and no committer, and asking for the wrong one drops it."""
    git(tmp_git_repo, "tag", "-a", "v2.0.0", "-m", "release")

    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        offered = await _offered(client)

    assert "v2.0.0" in [version["label"] for version in offered if version["kind"] == "ref"]


async def test_a_ref_whose_name_begins_with_a_dash_is_never_a_base(
    tmp_git_repo: Path, tmp_path_factory: pytest.TempPathFactory, reviews: ReviewFactory
) -> None:
    """Git allows the name, and `git diff` would read it as an option."""
    target = tmp_path_factory.mktemp("outside") / "written-by-git"
    git(tmp_git_repo, "update-ref", f"refs/heads/--output={target}", "HEAD")

    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        offered = await _offered(client)
        asked = await client.get(DIFF_ROUTE, params={"base": f"ref:--output={target}"}, headers=LOCAL_HEADERS)

    assert [version for version in offered if version["label"].startswith("-")] == []
    assert asked.status_code == HTTPStatus.BAD_REQUEST
    # Off the loop: touching the filesystem from an async test blocks it, and
    # what this asserts is precisely that nothing touched the filesystem
    assert not await asyncio.to_thread(target.exists)


async def test_a_repository_with_nothing_committed_still_offers_its_bases(
    tmp_path: Path, reviews: ReviewFactory
) -> None:
    """No HEAD means no refs to read against; the review itself is read against nothing, and counts every file."""
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    git(fresh, "init", "-b", "main")
    (fresh / "started.py").write_text("nothing committed yet\n")

    async with http_client(reviews.app(await repository_opening(fresh))) as client:
        offered = await _offered(client)

    assert [version["key"] for version in offered] == ["review"]
    assert offered[0]["changed"] == 1


async def test_a_base_on_no_commit_is_refused_rather_than_failed(tmp_path: Path, reviews: ReviewFactory) -> None:
    """HEAD names nothing yet in a new repository; asked for anyway, it is the reader's question that is wrong."""
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    git(fresh, "init", "-b", "main")
    (fresh / "started.py").write_text("nothing committed yet\n")

    async with http_client(reviews.app(await repository_opening(fresh))) as client:
        asked = await client.get(DIFF_ROUTE, params={"base": "ref:HEAD"}, headers=LOCAL_HEADERS)

    assert asked.status_code == HTTPStatus.BAD_REQUEST


async def test_a_count_git_will_not_take_is_not_a_count_of_zero(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """A reader told nothing changed stops looking; one told nothing stops trusting the count."""
    (tmp_git_repo / "work.py").write_text("under review\n")

    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        # An index git cannot read: the tree cannot be staged to be counted
        (tmp_git_repo / ".git" / "index").write_bytes(b"not an index")
        offered = await _offered(client)

    assert offered[0]["changed"] is None


async def test_the_diff_says_how_far_the_tree_has_moved_since_it_was_taken(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """A review reloaded while the tree was moving heard the push and lost it."""
    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        await _mark(client)
        (tmp_git_repo / "moved_after.py").write_text("written while the review was open\n")

        served = (await client.get(DIFF_ROUTE, headers=LOCAL_HEADERS)).json()

    assert served["moved"] == 1


async def test_a_review_opens_on_the_tree_its_first_round_is_marked_at(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """Whatever changed between reading the diff and serving it is on screen, so "since round 1" counts from there."""
    opening = await repository_opening(tmp_git_repo)
    (tmp_git_repo / "written_in_between.py").write_text("saved while the review was starting\n")

    async with http_client(reviews.app(opening)) as client:
        served = (await client.get(DIFF_ROUTE, headers=LOCAL_HEADERS)).json()
        by_key = {version["key"]: version for version in await _offered(client)}

    assert [file["path"] for file in served["files"]] == ["written_in_between.py"]
    assert "round:1" not in by_key, "nothing has changed since the tree round 1 began at"


def _commit_everything(repo: Path, message: str) -> None:
    git(repo, "add", ".")
    git(repo, "commit", "-m", message)


async def _paths_on_screen(client: AsyncClient) -> list[str]:
    return sorted(file["path"] for file in (await client.get(DIFF_ROUTE, headers=LOCAL_HEADERS)).json()["files"])


async def test_a_commit_made_during_the_review_leaves_its_diff_and_its_threads_as_they_were(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """The agent commits its work, as agents do: the review is of that work, and must not lose it to the commit."""
    (tmp_git_repo / "work.py").write_text("written for review\n")
    on_the_work = {**line_json("work.py", 1), "quote": ["written for review"]}

    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        _commit_everything(tmp_git_repo, "the agent's work")
        await _mark(client)
        on_screen = await _paths_on_screen(client)
        followed = (await client.post(FOLLOW_ROUTE, json={"anchors": [on_the_work]}, headers=LOCAL_HEADERS)).json()[
            "anchors"
        ]

    assert on_screen == ["work.py"]
    assert [anchor["outdated"] for anchor in followed] == [False]


async def test_a_review_against_an_earlier_commit_keeps_that_commit_on_screen_as_more_are_made(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """`--base HEAD~1` names the commit before the one under review; the next commit must not move it past that one."""
    (tmp_git_repo / "under_review.py").write_text("the commit under review\n")
    _commit_everything(tmp_git_repo, "the commit under review")
    opening = await open_diff(tmp_git_repo, "HEAD~1", GitRepository(objects=None))

    async with http_client(reviews.app(opening)) as client:
        (tmp_git_repo / "the_fix.py").write_text("what the round asked for\n")
        _commit_everything(tmp_git_repo, "the agent's fix")
        await _mark(client)
        on_screen = await _paths_on_screen(client)
        phrase = (await client.get(DIFF_ROUTE, headers=LOCAL_HEADERS)).json()["base"]["phrase"]

    assert on_screen == ["the_fix.py", "under_review.py"]
    assert phrase == "changes since HEAD~1", "the reader's own words name what the review is against"


async def test_a_review_whose_base_branch_is_deleted_still_takes_its_diff_again(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """The base is the commit the branch named when the review opened, which outlives the branch."""
    git(tmp_git_repo, "branch", "feature-base")
    (tmp_git_repo / "feature.py").write_text("on the feature\n")
    _commit_everything(tmp_git_repo, "the feature")
    opening = await open_diff(tmp_git_repo, "feature-base", GitRepository(objects=None))

    async with http_client(reviews.app(opening)) as client:
        git(tmp_git_repo, "branch", "-D", "feature-base")
        retaken = await client.post(RETAKE_ROUTE, json={}, headers=LOCAL_HEADERS)
        on_screen = await _paths_on_screen(client)

    assert retaken.status_code == HTTPStatus.OK
    assert on_screen == ["feature.py"]


async def test_a_tag_on_anything_but_a_commit_is_neither_offered_nor_taken_as_a_base(
    tmp_git_repo: Path, reviews: ReviewFactory
) -> None:
    """A tag may point at a blob, as git.git's own key does; nothing can be compared against one."""
    blob = git(tmp_git_repo, "hash-object", "-w", "initial.txt").strip()
    git(tmp_git_repo, "tag", "-a", "key-blob", blob, "-m", "a key, kept as a tag")
    git(tmp_git_repo, "tag", "plain-blob", blob)

    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as client:
        offered = [version["label"] for version in await _offered(client) if version["kind"] == "ref"]
        asked = [
            (await client.get(DIFF_ROUTE, params={"base": f"ref:{name}"}, headers=LOCAL_HEADERS)).status_code
            for name in ("key-blob", "plain-blob")
        ]

    assert "key-blob" not in offered
    assert "plain-blob" not in offered
    assert asked == [HTTPStatus.BAD_REQUEST, HTTPStatus.BAD_REQUEST]


async def test_a_first_commit_made_during_the_review_of_a_new_repository_leaves_its_diff_as_it_was(
    tmp_path: Path, reviews: ReviewFactory
) -> None:
    """With nothing committed the review is of everything there, and the first commit takes none of it away."""
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    git(fresh, "init", "-b", "main")
    git(fresh, "config", "user.email", "test@test.com")
    git(fresh, "config", "user.name", "Test")
    (fresh / "started.py").write_text("the first file of a new project\n")

    async with http_client(reviews.app(await repository_opening(fresh))) as client:
        _commit_everything(fresh, "the first commit")
        await _mark(client)
        on_screen = await _paths_on_screen(client)

    assert on_screen == ["started.py"]

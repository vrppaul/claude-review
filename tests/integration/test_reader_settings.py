"""The reader's settings and how far they have been shown around, kept for every review.

Every review runs on a port of its own, and a browser keeps one store per
port, so a choice kept there was gone in the next repository's review. The
server keeps them in the reader's own files instead.
"""

import asyncio
from contextlib import AbstractAsyncContextManager
from http import HTTPStatus
from pathlib import Path

import pytest
from httpx import AsyncClient

from claude_review.hosting.workspace import ReaderFiles
from tests.helpers import ReviewFactory, http_client, opening_of


@pytest.fixture
def reader_files(tmp_path: Path) -> ReaderFiles:
    """A reader no review on this machine has kept anything about."""
    return ReaderFiles(settings=tmp_path / "config" / "settings.json", guide=tmp_path / "state" / "guide.json")


def _client(reviews: ReviewFactory) -> AbstractAsyncContextManager[AsyncClient]:
    """A review of nothing in particular: what it remembers is the reader's, not its own."""
    return http_client(reviews.app(opening_of([])))


async def test_a_reader_who_never_chose_gets_the_defaults_and_is_told_so(reviews: ReviewFactory) -> None:
    async with _client(reviews) as client:
        seen = (await client.get("/api/settings")).json()

    assert seen == {
        "record": {
            "theme": "system",
            "diff_layout": "unified",
            "ignore_whitespace": False,
            "sound_on_replies": False,
        },
        "stored": False,
    }


async def test_a_choice_made_in_one_review_is_there_in_the_next(reviews: ReviewFactory) -> None:
    async with _client(reviews) as client:
        await client.put("/api/settings", json={"theme": "dark"})
    async with _client(reviews) as another_review:
        seen = (await another_review.get("/api/settings")).json()

    assert seen["record"]["theme"] == "dark"
    assert seen["stored"] is True


async def test_changing_one_choice_leaves_the_others_alone(reviews: ReviewFactory) -> None:
    async with _client(reviews) as client:
        await client.put("/api/settings", json={"diff_layout": "split"})
        changed = (await client.put("/api/settings", json={"ignore_whitespace": True})).json()

    assert (changed["diff_layout"], changed["ignore_whitespace"]) == ("split", True)


async def test_a_choice_the_review_does_not_know_is_refused(reviews: ReviewFactory, reader_files: ReaderFiles) -> None:
    async with _client(reviews) as client:
        unknown = await client.put("/api/settings", json={"font": "large"})
        wrong = await client.put("/api/settings", json={"theme": "sepia"})

    assert (unknown.status_code, wrong.status_code) == (422, 422)
    assert not reader_files.settings.exists()


async def test_the_release_a_reader_was_shown_is_remembered(reviews: ReviewFactory) -> None:
    async with _client(reviews) as client:
        before = (await client.get("/api/guide")).json()
        await client.put("/api/guide", json={"seen_release": "1.5.0"})
        after = (await client.get("/api/guide")).json()

    assert before == {"record": {"seen_release": None}, "stored": False}
    assert after == {"record": {"seen_release": "1.5.0"}, "stored": True}


async def test_settings_and_what_was_shown_are_kept_apart(reviews: ReviewFactory, reader_files: ReaderFiles) -> None:
    """Configuration is often kept in git; a release number changing there would be noise."""
    async with _client(reviews) as client:
        await client.put("/api/guide", json={"seen_release": "1.5.0"})

    assert reader_files.guide.exists()
    assert not reader_files.settings.exists()


async def test_a_choice_sent_as_null_is_a_choice_not_sent(reviews: ReviewFactory) -> None:
    async with _client(reviews) as client:
        await client.put("/api/settings", json={"theme": "dark"})
        response = await client.put("/api/settings", json={"theme": None, "diff_layout": "split"})

    assert response.status_code == HTTPStatus.OK
    assert (response.json()["theme"], response.json()["diff_layout"]) == ("dark", "split")


async def test_settings_changed_together_are_all_kept(reviews: ReviewFactory) -> None:
    async with _client(reviews) as client:
        await asyncio.gather(
            client.put("/api/settings", json={"theme": "dark"}),
            client.put("/api/settings", json={"diff_layout": "split"}),
            client.put("/api/settings", json={"sound_on_replies": True}),
        )
        kept = (await client.get("/api/settings")).json()["record"]

    assert (kept["theme"], kept["diff_layout"], kept["sound_on_replies"]) == ("dark", "split", True)

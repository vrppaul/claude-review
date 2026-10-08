"""The reader's settings and how far they have been shown around, kept for every review.

Every review runs on a port of its own, and a browser keeps one store per
port, so a choice kept there was gone in the next repository's review. The
server keeps them in the reader's own files instead.
"""

import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from claude_review.domain.models import ReaderFiles, ReviewMode, ReviewWorkspace
from claude_review.presentation.app import create_app
from claude_review.presentation.state import ServerState

LOCAL_ORIGIN = "http://127.0.0.1:8000"


def _client(workspace: ReviewWorkspace, reader_files: ReaderFiles) -> AsyncClient:
    state = ServerState(shutdown_event=asyncio.Event())
    app = create_app(diff_files=[], state=state, mode=ReviewMode.DIFF, workspace=workspace, reader_files=reader_files)
    return AsyncClient(transport=ASGITransport(app=app), base_url=LOCAL_ORIGIN)


@pytest.fixture
def fresh_reader(tmp_path: Path) -> ReaderFiles:
    """A reader no review on this machine has kept anything about."""
    return ReaderFiles(settings=tmp_path / "config" / "settings.json", guide=tmp_path / "state" / "guide.json")


async def test_a_reader_who_never_chose_gets_the_defaults_and_is_told_so(
    workspace: ReviewWorkspace, fresh_reader: ReaderFiles
) -> None:
    async with _client(workspace, fresh_reader) as client:
        seen = (await client.get("/api/settings")).json()

    assert seen == {
        "settings": {
            "theme": "system",
            "diff_layout": "unified",
            "ignore_whitespace": False,
            "sound_on_replies": False,
        },
        "stored": False,
    }


async def test_a_choice_made_in_one_review_is_there_in_the_next(
    workspace: ReviewWorkspace, fresh_reader: ReaderFiles
) -> None:
    async with _client(workspace, fresh_reader) as client:
        await client.put("/api/settings", json={"theme": "dark"})
    async with _client(workspace, fresh_reader) as another_review:
        seen = (await another_review.get("/api/settings")).json()

    assert seen["settings"]["theme"] == "dark"
    assert seen["stored"] is True


async def test_changing_one_choice_leaves_the_others_alone(
    workspace: ReviewWorkspace, fresh_reader: ReaderFiles
) -> None:
    async with _client(workspace, fresh_reader) as client:
        await client.put("/api/settings", json={"diff_layout": "split"})
        changed = (await client.put("/api/settings", json={"ignore_whitespace": True})).json()

    assert (changed["diff_layout"], changed["ignore_whitespace"]) == ("split", True)


async def test_a_choice_the_review_does_not_know_is_refused(
    workspace: ReviewWorkspace, fresh_reader: ReaderFiles
) -> None:
    async with _client(workspace, fresh_reader) as client:
        unknown = await client.put("/api/settings", json={"font": "large"})
        wrong = await client.put("/api/settings", json={"theme": "sepia"})

    assert (unknown.status_code, wrong.status_code) == (422, 422)
    assert not fresh_reader.settings.exists()


async def test_the_release_a_reader_was_shown_is_remembered(
    workspace: ReviewWorkspace, fresh_reader: ReaderFiles
) -> None:
    async with _client(workspace, fresh_reader) as client:
        before = (await client.get("/api/guide")).json()
        await client.put("/api/guide", json={"seen_release": "1.5.0"})
        after = (await client.get("/api/guide")).json()

    assert before == {"guide": {"seen_release": None}, "stored": False}
    assert after == {"guide": {"seen_release": "1.5.0"}, "stored": True}


async def test_settings_and_what_was_shown_are_kept_apart(
    workspace: ReviewWorkspace, fresh_reader: ReaderFiles
) -> None:
    """Configuration is often kept in git; a release number changing there would be noise."""
    async with _client(workspace, fresh_reader) as client:
        await client.put("/api/guide", json={"seen_release": "1.5.0"})

    assert fresh_reader.guide.exists()
    assert not fresh_reader.settings.exists()


async def test_a_choice_sent_as_null_is_a_choice_not_sent(
    workspace: ReviewWorkspace, fresh_reader: ReaderFiles
) -> None:
    async with _client(workspace, fresh_reader) as client:
        await client.put("/api/settings", json={"theme": "dark"})
        response = await client.put("/api/settings", json={"theme": None, "diff_layout": "split"})

    assert response.status_code == 200
    assert (response.json()["theme"], response.json()["diff_layout"]) == ("dark", "split")


async def test_settings_changed_together_are_all_kept(workspace: ReviewWorkspace, fresh_reader: ReaderFiles) -> None:
    async with _client(workspace, fresh_reader) as client:
        await asyncio.gather(
            client.put("/api/settings", json={"theme": "dark"}),
            client.put("/api/settings", json={"diff_layout": "split"}),
            client.put("/api/settings", json={"sound_on_replies": True}),
        )
        kept = (await client.get("/api/settings")).json()["settings"]

    assert (kept["theme"], kept["diff_layout"], kept["sound_on_replies"]) == ("dark", "split", True)

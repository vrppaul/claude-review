"""Pasted images over HTTP: a screenshot says what a paragraph cannot.

The reader pastes an image into the panel or a thread; the server keeps it
in the review's workspace, and what goes to the agent — a message, a
question, a round — names a path it can open. The
rules themselves are tested without a server in test_image_service.
"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import AsyncClient

from claude_review.domain.models import ReviewMode, ReviewWorkspace
from claude_review.services.image_service import MAX_IMAGE_BYTES, MAX_IMAGES_PER_MESSAGE, MAX_REVIEW_BYTES
from tests.helpers import DIFF_ROUTE, EVENTS_ROUTE, REVIEWED_FILE, WAIT_FOR_EVENT, ReviewFactory, http_client

# The bytes each format starts with, and enough after them to be a file
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
GIF = b"GIF89a" + b"\x00" * 32
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 16
NEVER_KEPT = f"{'0' * 32}.png"
# The largest image the review takes, a PNG to the last byte
LARGEST_IMAGE = PNG + b"\x00" * (MAX_IMAGE_BYTES - len(PNG))
# How many of the largest images fill a review to its limit
LARGEST_IMAGES_A_REVIEW_HOLDS = MAX_REVIEW_BYTES // MAX_IMAGE_BYTES
# One image past what one thing said may carry
ONE_TOO_MANY = MAX_IMAGES_PER_MESSAGE + 1

THREAD_COMMENT = {
    "anchor": {"file": REVIEWED_FILE, "side": "new", "start_line": 1, "end_line": 1},
    "severity": "note",
    "body": "Looks off",
}
A_QUESTION = {
    **THREAD_COMMENT,
    "thread_id": "comment-1",
    "question_id": "comment-1",
    "resolved": False,
    "raised_by": "reader",
}


@pytest.fixture
async def client(reviews: ReviewFactory) -> AsyncIterator[AsyncClient]:
    async with http_client(reviews.app([], mode=ReviewMode.FILES)) as agent:
        yield agent


async def _upload(client: AsyncClient, content: bytes) -> str:
    response = await client.post("/api/images", content=content, headers={"Content-Type": "image/png"})
    assert response.status_code == 200, response.text
    return response.json()["image_id"]


async def _files_in(directory: Path) -> list[Path]:
    # Off the loop: what these assert is what reached the filesystem
    return await asyncio.to_thread(lambda: list(directory.iterdir()))


async def test_an_image_is_kept_and_served_back(client: AsyncClient) -> None:
    """What was pasted is what the panel draws."""
    image_id = await _upload(client, PNG)

    served = await client.get(f"/api/images/{image_id}")

    assert served.status_code == 200
    assert served.content == PNG
    assert served.headers["content-type"] == "image/png"


async def test_what_is_not_an_image_is_refused(client: AsyncClient) -> None:
    response = await client.post("/api/images", content=b"<svg onload=alert(1)>")

    assert response.status_code == 422


@pytest.mark.parametrize("content", [JPEG, GIF, WEBP], ids=["jpeg", "gif", "webp"])
async def test_every_format_a_browser_pastes_is_kept(client: AsyncClient, content: bytes) -> None:
    image_id = await _upload(client, content)

    assert (await client.get(f"/api/images/{image_id}")).content == content


async def test_an_empty_upload_is_refused(client: AsyncClient) -> None:
    assert (await client.post("/api/images", content=b"")).status_code == 422


async def test_a_review_full_of_images_takes_no_more(client: AsyncClient) -> None:
    """Pasting and removing in a loop would otherwise fill the disk the review lives on."""
    for _ in range(LARGEST_IMAGES_A_REVIEW_HOLDS):
        await _upload(client, LARGEST_IMAGE)

    response = await client.post("/api/images", content=PNG)

    assert response.status_code == 413


@pytest.mark.parametrize(
    ("route", "payload"),
    [
        ("/api/message", {"message_id": "panel-1", "text": "These"}),
        ("/api/ask", A_QUESTION),
    ],
    ids=["message", "ask"],
)
async def test_one_thing_said_carries_no_more_images_than_it_may(
    client: AsyncClient, route: str, payload: dict[str, object]
) -> None:
    """More than a handful is a gallery. The image is one the review keeps, so the count alone is refused."""
    image_id = await _upload(client, PNG)

    response = await client.post(route, json={**payload, "images": [image_id] * ONE_TOO_MANY})

    assert response.status_code == 422


async def test_a_thread_in_a_round_carries_no_more_images_than_it_may(client: AsyncClient) -> None:
    image_id = await _upload(client, PNG)
    crowded = {**THREAD_COMMENT, "images": [image_id] * ONE_TOO_MANY}

    response = await client.post("/api/submit", json={"comments": [crowded]})

    assert response.status_code == 422


async def test_an_image_too_large_is_refused_before_it_is_written(
    client: AsyncClient, workspace: ReviewWorkspace
) -> None:
    response = await client.post("/api/images", content=PNG + b"\x00" * MAX_IMAGE_BYTES)

    assert response.status_code == 413
    assert await _files_in(workspace.images) == []


async def test_a_message_hands_the_agent_a_file_it_can_open(client: AsyncClient) -> None:
    """The agent reads files, so the image travels as a path to one."""
    image_id = await _upload(client, PNG)
    await client.post("/api/message", json={"message_id": "panel-1", "text": "This", "images": [image_id]})

    event = (await client.get(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()

    [path] = event["message"]["images"]
    assert Path(path).is_absolute()
    assert await asyncio.to_thread(Path(path).read_bytes) == PNG


async def test_an_image_can_be_the_whole_message(client: AsyncClient) -> None:
    image_id = await _upload(client, PNG)

    response = await client.post("/api/message", json={"message_id": "panel-1", "images": [image_id]})

    assert response.status_code == 200


async def test_a_message_with_neither_words_nor_images_is_refused(client: AsyncClient) -> None:
    response = await client.post("/api/message", json={"message_id": "panel-1", "text": "  "})

    assert response.status_code == 422


async def test_a_message_naming_an_image_never_kept_is_refused(client: AsyncClient) -> None:
    message = {"message_id": "panel-1", "text": "This", "images": [NEVER_KEPT]}

    response = await client.post("/api/message", json=message)

    assert response.status_code == 422


async def test_an_image_never_kept_is_not_there(client: AsyncClient) -> None:
    assert (await client.get(f"/api/images/{NEVER_KEPT}")).status_code == 404
    assert (await client.delete(f"/api/images/{NEVER_KEPT}")).status_code == 404


async def test_the_catch_up_lists_the_images_said_in_the_panel(client: AsyncClient) -> None:
    """An agent arriving late finds the screenshot along with the words."""
    image_id = await _upload(client, PNG)
    await client.post("/api/message", json={"message_id": "panel-1", "text": "This", "images": [image_id]})

    context = (await client.get("/api/context")).json()

    [entry] = context["panel"]
    assert Path(entry["images"][0]).name == image_id


async def test_an_image_taken_off_before_sending_is_removed(client: AsyncClient, workspace: ReviewWorkspace) -> None:
    """Otherwise pasting and removing in a loop fills the disk."""
    image_id = await _upload(client, PNG)

    response = await client.delete(f"/api/images/{image_id}")

    assert response.status_code == 200
    assert await _files_in(workspace.images) == []


async def test_an_image_already_sent_stays(client: AsyncClient) -> None:
    """The agent may not have opened it yet."""
    image_id = await _upload(client, PNG)
    await client.post("/api/message", json={"message_id": "panel-1", "images": [image_id]})

    response = await client.delete(f"/api/images/{image_id}")

    assert response.status_code == 409
    assert (await client.get(f"/api/images/{image_id}")).status_code == 200


async def test_the_browser_is_told_the_limits(client: AsyncClient) -> None:
    """So it checks them before uploading rather than repeating the numbers."""
    limits = (await client.get(DIFF_ROUTE)).json()["image_limits"]

    assert limits == {"max_image_bytes": MAX_IMAGE_BYTES, "max_images_per_message": MAX_IMAGES_PER_MESSAGE}


async def test_a_round_names_the_images_in_its_threads(client: AsyncClient) -> None:
    image_id = await _upload(client, PNG)

    response = await client.post("/api/submit", json={"comments": [{**THREAD_COMMENT, "images": [image_id]}]})

    assert f"/{image_id}" in response.json()["markdown"]


async def test_an_image_lost_from_a_thread_does_not_hold_up_the_round(client: AsyncClient) -> None:
    """A thread outlives a restart in the reader's draft; its screenshots do not."""
    response = await client.post("/api/submit", json={"comments": [{**THREAD_COMMENT, "images": [NEVER_KEPT]}]})

    assert response.status_code == 200
    assert NEVER_KEPT not in response.json()["markdown"]


async def test_a_question_hands_the_agent_its_images(client: AsyncClient) -> None:
    image_id = await _upload(client, PNG)

    await client.post("/api/ask", json={**A_QUESTION, "body": "", "images": [image_id]})
    event = (await client.get(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()

    [path] = event["question"]["images"]
    assert Path(path).name == image_id

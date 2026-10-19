"""Pasted images over HTTP: a screenshot says what a paragraph cannot.

The reader pastes an image into the panel or a thread; the server keeps it
in the review's workspace, and what goes to the agent — a message, a
question, a round — names a path it can open. The
rules themselves are tested without a server in test_image_service.
"""

import asyncio
from collections.abc import AsyncIterator
from http import HTTPStatus
from pathlib import Path

import pytest
from httpx import AsyncClient
from structlog.typing import EventDict

from claude_review.domain.models import LARGEST_FILE_SHOWN_BYTES, MAX_QUOTE_LINES, ReviewMode, TurnAuthor
from claude_review.hosting.workspace import ReviewWorkspace
from claude_review.presentation.wire.base import MAX_TEXT_LENGTH
from claude_review.services.file_window_service import MAX_WINDOW_LINES
from claude_review.services.image_service import MAX_IMAGE_BYTES, MAX_IMAGES_PER_MESSAGE, MAX_REVIEW_BYTES
from tests.helpers import (
    CONVERSATION_ROUTE,
    EVENTS_ROUTE,
    FIRST_THREAD_ID,
    IMAGES_ROUTE,
    PNG,
    REVIEW_ROUTE,
    REVIEWED_FILE,
    WAIT_FOR_EVENT,
    ReviewFactory,
    UploadThatBreaksOff,
    http_client,
    line_on_the_wire,
    opening_of,
    thread_on_the_wire,
    turn_on_the_wire,
)

# The bytes each format starts with, and enough after them to be a file
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
# The levels a log line is written at when someone should look into it
WORTH_A_LOOK = frozenset({"warning", "error", "critical"})

A_THREAD = thread_on_the_wire(line_on_the_wire(REVIEWED_FILE, 1), "Looks off")


@pytest.fixture
async def client(reviews: ReviewFactory) -> AsyncIterator[AsyncClient]:
    async with http_client(reviews.app(opening_of([], mode=ReviewMode.FILES))) as agent:
        yield agent


async def _upload(client: AsyncClient, content: bytes) -> str:
    response = await client.post("/api/images", content=content, headers={"Content-Type": "image/png"})
    assert response.status_code == HTTPStatus.OK, response.text
    return response.json()["image_id"]


async def _files_in(directory: Path) -> list[Path]:
    # Off the loop: what these assert is what reached the filesystem
    return await asyncio.to_thread(lambda: list(directory.iterdir()))


async def test_an_image_is_kept_and_served_back(client: AsyncClient) -> None:
    """What was pasted is what the panel draws."""
    image_id = await _upload(client, PNG)

    served = await client.get(f"/api/images/{image_id}")

    assert served.status_code == HTTPStatus.OK
    assert served.content == PNG
    assert served.headers["content-type"] == "image/png"


async def test_what_is_not_an_image_is_refused(client: AsyncClient) -> None:
    response = await client.post("/api/images", content=b"<svg onload=alert(1)>")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


@pytest.mark.parametrize("content", [JPEG, GIF, WEBP], ids=["jpeg", "gif", "webp"])
async def test_every_format_a_browser_pastes_is_kept(client: AsyncClient, content: bytes) -> None:
    image_id = await _upload(client, content)

    assert (await client.get(f"/api/images/{image_id}")).content == content


async def test_a_review_full_of_images_takes_no_more(client: AsyncClient) -> None:
    """Pasting and removing in a loop would otherwise fill the disk the review lives on."""
    for _ in range(LARGEST_IMAGES_A_REVIEW_HOLDS):
        await _upload(client, LARGEST_IMAGE)

    response = await client.post("/api/images", content=PNG)

    assert response.status_code == HTTPStatus.CONTENT_TOO_LARGE


async def test_a_message_carries_no_more_images_than_it_may(client: AsyncClient) -> None:
    """More than a handful is a gallery. The image is one the review keeps, so the count alone is refused."""
    image_id = await _upload(client, PNG)

    response = await client.post(
        "/api/message", json={"message_id": "panel-1", "body": "These", "images": [image_id] * ONE_TOO_MANY}
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_a_question_carries_no_more_images_than_it_may(client: AsyncClient) -> None:
    image_id = await _upload(client, PNG)
    crowded = {**A_THREAD, "images": [image_id] * ONE_TOO_MANY}

    response = await client.post("/api/ask", json={"question_id": FIRST_THREAD_ID, "thread": crowded})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_a_thread_in_a_round_carries_no_more_images_than_it_may(client: AsyncClient) -> None:
    image_id = await _upload(client, PNG)
    crowded = {**A_THREAD, "images": [image_id] * ONE_TOO_MANY}

    response = await client.post("/api/submit", json={"threads": [crowded], "end": True})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_an_image_too_large_is_refused_before_it_is_written(
    client: AsyncClient, workspace: ReviewWorkspace
) -> None:
    response = await client.post("/api/images", content=PNG + b"\x00" * MAX_IMAGE_BYTES)

    assert response.status_code == HTTPStatus.CONTENT_TOO_LARGE
    assert await _files_in(workspace.images) == []


async def test_an_upload_the_browser_breaks_off_is_dropped_without_a_refusal(
    reviews: ReviewFactory, workspace: ReviewWorkspace, logged: list[EventDict]
) -> None:
    """Nobody is left to be told no, and a refusal in the log would read as something gone wrong."""
    review = reviews.app(opening_of([], mode=ReviewMode.FILES))

    await UploadThatBreaksOff(first_part=PNG).upload(review)

    assert await _files_in(workspace.images) == []
    assert [entry["event"] for entry in logged if entry["log_level"] in WORTH_A_LOOK] == []


async def test_a_message_hands_the_agent_a_file_it_can_open(client: AsyncClient) -> None:
    """The agent reads files, so the image travels as a path to one."""
    image_id = await _upload(client, PNG)
    await client.post("/api/message", json={"message_id": "panel-1", "body": "This", "images": [image_id]})

    event = (await client.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()

    [path] = event["message"]["images"]
    assert Path(path).is_absolute()
    assert await asyncio.to_thread(Path(path).read_bytes) == PNG


async def test_an_image_can_be_the_whole_message(client: AsyncClient) -> None:
    image_id = await _upload(client, PNG)

    response = await client.post("/api/message", json={"message_id": "panel-1", "images": [image_id]})

    assert response.status_code == HTTPStatus.NO_CONTENT


async def test_a_message_with_neither_words_nor_images_is_refused(client: AsyncClient) -> None:
    response = await client.post("/api/message", json={"message_id": "panel-1", "body": "  "})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_a_message_naming_an_image_never_kept_is_refused(client: AsyncClient) -> None:
    message = {"message_id": "panel-1", "body": "This", "images": [NEVER_KEPT]}

    response = await client.post("/api/message", json=message)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_an_image_never_kept_is_not_there(client: AsyncClient) -> None:
    assert (await client.get(f"/api/images/{NEVER_KEPT}")).status_code == HTTPStatus.NOT_FOUND
    assert (await client.delete(f"/api/images/{NEVER_KEPT}")).status_code == HTTPStatus.NOT_FOUND


async def test_the_catch_up_lists_the_images_said_in_the_panel(client: AsyncClient) -> None:
    """An agent arriving late finds the screenshot along with the words."""
    image_id = await _upload(client, PNG)
    await client.post("/api/message", json={"message_id": "panel-1", "body": "This", "images": [image_id]})

    context = (await client.get("/api/catch-up")).json()

    [entry] = context["panel"]
    assert Path(entry["images"][0]).name == image_id


async def test_a_page_opening_draws_an_image_said_in_the_panel_by_the_id_it_is_kept_under(client: AsyncClient) -> None:
    """The page asks the review for it by that id, as it drew it the moment it was sent."""
    image_id = await _upload(client, PNG)
    await client.post("/api/message", json={"message_id": "panel-1", "body": "This", "images": [image_id]})

    [said] = (await client.get(CONVERSATION_ROUTE)).json()["said"]

    assert said["images"] == [image_id]
    assert (await client.get(f"{IMAGES_ROUTE}/{image_id}")).status_code == HTTPStatus.OK


async def test_an_image_taken_off_before_sending_is_removed(client: AsyncClient, workspace: ReviewWorkspace) -> None:
    """Otherwise pasting and removing in a loop fills the disk."""
    image_id = await _upload(client, PNG)

    response = await client.delete(f"/api/images/{image_id}")

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert await _files_in(workspace.images) == []


async def test_an_image_already_sent_stays(client: AsyncClient) -> None:
    """The agent may not have opened it yet."""
    image_id = await _upload(client, PNG)
    await client.post("/api/message", json={"message_id": "panel-1", "images": [image_id]})

    response = await client.delete(f"/api/images/{image_id}")

    assert response.status_code == HTTPStatus.CONFLICT
    assert (await client.get(f"/api/images/{image_id}")).status_code == HTTPStatus.OK


async def test_the_browser_is_told_the_limits(client: AsyncClient) -> None:
    """So it checks them before sending rather than repeating the numbers."""
    limits = (await client.get(REVIEW_ROUTE)).json()["limits"]

    assert limits == {
        "max_image_bytes": MAX_IMAGE_BYTES,
        "max_images_per_message": MAX_IMAGES_PER_MESSAGE,
        "max_quoted_lines": MAX_QUOTE_LINES,
        "max_window_lines": MAX_WINDOW_LINES,
        "max_text_length": MAX_TEXT_LENGTH,
        "largest_file_shown_bytes": LARGEST_FILE_SHOWN_BYTES,
    }


async def test_a_round_names_the_images_in_its_threads(client: AsyncClient) -> None:
    image_id = await _upload(client, PNG)

    response = await client.post("/api/submit", json={"threads": [{**A_THREAD, "images": [image_id]}], "end": True})

    assert f"/{image_id}" in response.json()["markdown"]


async def test_an_image_lost_from_a_thread_does_not_hold_up_the_round(client: AsyncClient) -> None:
    """A thread outlives a restart in the reader's draft; its screenshots do not."""
    response = await client.post("/api/submit", json={"threads": [{**A_THREAD, "images": [NEVER_KEPT]}], "end": True})

    assert response.status_code == HTTPStatus.OK
    assert NEVER_KEPT not in response.json()["markdown"]


async def test_a_question_hands_the_agent_its_images(client: AsyncClient) -> None:
    image_id = await _upload(client, PNG)

    pictured = {**A_THREAD, "body": "", "images": [image_id]}

    await client.post("/api/ask", json={"question_id": FIRST_THREAD_ID, "thread": pictured})
    event = (await client.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()

    [path] = event["question"]["images"]
    assert Path(path).name == image_id


async def test_a_question_asked_in_a_reply_hands_the_agent_the_images_of_that_reply(client: AsyncClient) -> None:
    image_id = await _upload(client, PNG)
    reply = turn_on_the_wire(TurnAuthor.READER, "Still like this", turn_id="turn-1", images=[image_id])

    await client.post("/api/ask", json={"question_id": "turn-1", "thread": {**A_THREAD, "turns": [reply]}})
    event = (await client.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()

    [path] = event["question"]["images"]
    assert Path(path).name == image_id
    # Asked, so handed over: the agent may open it at any time from now on
    assert (await client.delete(f"/api/images/{image_id}")).status_code == HTTPStatus.CONFLICT

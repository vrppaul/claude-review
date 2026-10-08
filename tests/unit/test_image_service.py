"""What a review accepts as an image, and how it keeps count.

The rules, with no disk: the store is a dictionary, so each test says only
what was pasted and what the review decided. What the review has room for
is read back the way the reader meets it — by what it refuses next.
"""

import asyncio
from pathlib import Path

import pytest

from claude_review.domain.exceptions import (
    ImageAlreadySentError,
    ImageRefusedError,
    ImageTooLargeError,
    UnknownImageError,
)
from claude_review.domain.models import ImageLedger
from claude_review.services.image_service import (
    MAX_IMAGE_BYTES,
    MAX_IMAGE_MEGABYTES,
    REVIEW_IMAGE_QUOTA,
    ImageQuota,
    ImageService,
    recognise,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 16
STORE_ROOT = Path("/review/images")
# A review with room for exactly one of the images these tests paste
ROOM_FOR_ONE = ImageQuota(image_bytes=len(PNG), review_bytes=len(PNG))
# A review with no room left for anything
FULL = ImageQuota(image_bytes=len(PNG), review_bytes=0)
# Long enough for an upload that is not held to finish however busy the machine is
SETTLED_SECONDS = 1


class MemoryImageStore:
    """An image store that keeps bytes in a dictionary."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def write(self, name: str, content: bytes) -> Path:
        self.files[name] = content
        return STORE_ROOT / name

    async def remove(self, name: str) -> None:
        self.files.pop(name, None)


class HeldImageStore(MemoryImageStore):
    """A store whose writes wait until the test lets them land, as a slow disk does."""

    def __init__(self) -> None:
        super().__init__()
        self.writing = asyncio.Event()
        self.released = asyncio.Event()

    async def write(self, name: str, content: bytes) -> Path:
        self.writing.set()
        await self.released.wait()
        return await super().write(name, content)


class InterruptedImageStore(MemoryImageStore):
    """A store whose first write never lands, the way a shutdown can stop one."""

    def __init__(self) -> None:
        super().__init__()
        self.interrupted = False

    async def write(self, name: str, content: bytes) -> Path:
        if not self.interrupted:
            self.interrupted = True
            raise asyncio.CancelledError
        return await super().write(name, content)


class StuckImageStore(MemoryImageStore):
    """A store whose files cannot be removed, the way a read-only disk refuses."""

    async def remove(self, name: str) -> None:
        raise PermissionError(name)


@pytest.fixture
def store() -> MemoryImageStore:
    return MemoryImageStore()


@pytest.fixture
def service(store: MemoryImageStore) -> ImageService:
    return ImageService(store, ImageLedger(), REVIEW_IMAGE_QUOTA)


def _with_room_for_one(store: MemoryImageStore) -> ImageService:
    return ImageService(store, ImageLedger(), ROOM_FOR_ONE)


def test_a_format_is_read_from_the_bytes() -> None:
    known = recognise(WEBP)

    assert known is not None
    assert known.media_type == "image/webp"


def test_webp_needs_its_container_too() -> None:
    """The name alone at the right place is not a WebP file."""
    assert recognise(b"<script>WEBP" + b"\x00" * 16) is None


async def test_a_kept_image_is_found_where_it_was_written(service: ImageService) -> None:
    stored = await service.keep(PNG)

    assert service.find(stored.image_id) == stored
    assert stored.path == STORE_ROOT / stored.image_id


async def test_a_kept_image_takes_up_room_in_the_review(store: MemoryImageStore) -> None:
    service = _with_room_for_one(store)
    await service.keep(PNG)

    with pytest.raises(ImageTooLargeError):
        await service.keep(PNG)


async def test_an_id_the_review_never_handed_out_finds_nothing(service: ImageService) -> None:
    """The ledger is the guard: no path is ever built from what the browser sends."""
    assert service.find("../../etc/passwd") is None


async def test_what_is_not_an_image_is_refused(service: ImageService, store: MemoryImageStore) -> None:
    with pytest.raises(ImageRefusedError, match="png"):
        await service.keep(b"<svg onload=alert(1)>")

    assert store.files == {}


async def test_an_image_over_its_limit_is_refused(service: ImageService) -> None:
    with pytest.raises(ImageTooLargeError, match=f"{MAX_IMAGE_MEGABYTES} MB"):
        await service.keep(PNG + b"\x00" * MAX_IMAGE_BYTES)


async def test_an_empty_upload_is_refused(service: ImageService) -> None:
    with pytest.raises(ImageRefusedError) as refused:
        await service.keep(b"")

    assert not isinstance(refused.value, ImageTooLargeError)


async def test_an_upload_while_another_is_still_writing_cannot_overshoot_the_review() -> None:
    """The second is measured against the first before the first has landed."""
    store = HeldImageStore()
    service = _with_room_for_one(store)
    first = asyncio.create_task(service.keep(PNG))
    await store.writing.wait()

    with pytest.raises(ImageTooLargeError):
        await asyncio.wait_for(service.keep(PNG), timeout=SETTLED_SECONDS)

    store.released.set()
    await first


async def test_handing_over_names_the_files_and_keeps_them(service: ImageService) -> None:
    stored = await service.keep(PNG)

    assert service.hand_over([stored.image_id]).paths == [stored.path]
    with pytest.raises(ImageAlreadySentError):
        await service.discard(stored.image_id)
    assert service.find(stored.image_id) == stored


async def test_handing_over_names_what_the_review_does_not_keep(service: ImageService) -> None:
    """Whether a missing image is a fault is for the caller to say."""
    stored = await service.keep(PNG)

    handover = service.hand_over([stored.image_id, "gone.png"])

    assert handover.paths == [stored.path]
    assert handover.missing == ["gone.png"]


async def test_a_discarded_image_gives_back_its_room(store: MemoryImageStore) -> None:
    service = _with_room_for_one(store)
    stored = await service.keep(PNG)

    await service.discard(stored.image_id)

    assert service.find(stored.image_id) is None
    assert store.files == {}
    assert (await service.keep(PNG)).size == len(PNG)


async def test_discarding_an_image_never_kept_is_refused(service: ImageService) -> None:
    with pytest.raises(UnknownImageError):
        await service.discard("nothing.png")


async def test_a_write_that_never_lands_gives_back_its_room() -> None:
    service = _with_room_for_one(InterruptedImageStore())

    with pytest.raises(asyncio.CancelledError):
        await service.keep(PNG)

    assert (await service.keep(PNG)).size == len(PNG)


async def test_what_is_not_an_image_is_named_so_even_in_a_full_review(store: MemoryImageStore) -> None:
    """The reader can fix a wrong format; a full review is a different problem."""
    service = ImageService(store, ImageLedger(), FULL)

    with pytest.raises(ImageRefusedError) as refused:
        await service.keep(b"not an image at all")

    assert not isinstance(refused.value, ImageTooLargeError)


async def test_an_image_named_twice_is_handed_over_once(service: ImageService) -> None:
    stored = await service.keep(PNG)

    assert service.hand_over([stored.image_id, stored.image_id]).paths == [stored.path]


async def test_requiring_names_the_images_the_review_does_not_keep(service: ImageService) -> None:
    stored = await service.keep(PNG)

    with pytest.raises(UnknownImageError, match=r"gone\.png"):
        service.require([stored.image_id, "gone.png"])
    # Refused as a whole: the one it does keep was not handed over, so it can still be taken off
    await service.discard(stored.image_id)


async def test_an_image_that_cannot_be_removed_is_still_counted() -> None:
    """What is on the disk is what the review holds, whatever the reader took off the message."""
    service = _with_room_for_one(StuckImageStore())
    stored = await service.keep(PNG)

    await service.discard(stored.image_id)

    assert service.find(stored.image_id) == stored
    with pytest.raises(ImageTooLargeError):
        await service.keep(PNG)

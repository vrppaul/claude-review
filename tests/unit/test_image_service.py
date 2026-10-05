"""What a review accepts as an image, and how it keeps count.

The rules, with no disk: the store is a dictionary, so each test says only
what was pasted and what the review decided.
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
from claude_review.services import image_service
from claude_review.services.image_service import MAX_IMAGE_BYTES, ImageService, recognise

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 16
STORE_ROOT = Path("/review/images")


class MemoryImageStore:
    """An image store that keeps bytes in a dictionary."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def write(self, name: str, content: bytes) -> Path:
        self.files[name] = content
        return STORE_ROOT / name

    async def remove(self, name: str) -> None:
        self.files.pop(name, None)


@pytest.fixture
def store() -> MemoryImageStore:
    return MemoryImageStore()


@pytest.fixture
def ledger() -> ImageLedger:
    return ImageLedger()


@pytest.fixture
def service(store: MemoryImageStore, ledger: ImageLedger) -> ImageService:
    return ImageService(store, ledger)


def test_a_format_is_read_from_the_bytes() -> None:
    known = recognise(WEBP)

    assert known is not None
    assert known.media_type == "image/webp"


def test_webp_needs_its_container_too() -> None:
    """The name alone at the right place is not a WebP file."""
    assert recognise(b"<script>WEBP" + b"\x00" * 16) is None


async def test_a_kept_image_is_counted_and_found(service: ImageService, ledger: ImageLedger) -> None:
    stored = await service.keep(PNG)

    assert service.find(stored.image_id) == stored
    assert ledger.held_bytes == len(PNG)
    assert stored.path == STORE_ROOT / stored.image_id


async def test_an_id_the_review_never_handed_out_finds_nothing(service: ImageService) -> None:
    """The ledger is the guard: no path is ever built from what the browser sends."""
    assert service.find("../../etc/passwd") is None


async def test_what_is_not_an_image_is_refused(service: ImageService, store: MemoryImageStore) -> None:
    with pytest.raises(ImageRefusedError, match="png"):
        await service.keep(b"<svg onload=alert(1)>")

    assert store.files == {}


async def test_an_image_over_its_limit_is_refused(service: ImageService) -> None:
    with pytest.raises(ImageTooLargeError, match="MB"):
        await service.keep(PNG + b"\x00" * MAX_IMAGE_BYTES)


async def test_two_uploads_at_once_cannot_overshoot_the_review(
    service: ImageService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The second is measured against the first before either is written."""
    monkeypatch.setattr(image_service, "MAX_REVIEW_BYTES", len(PNG) + 1)

    outcomes = await asyncio.gather(service.keep(PNG), service.keep(PNG), return_exceptions=True)

    assert sum(isinstance(outcome, ImageTooLargeError) for outcome in outcomes) == 1


async def test_handing_over_names_the_files_and_keeps_them(service: ImageService, ledger: ImageLedger) -> None:
    stored = await service.keep(PNG)

    assert service.hand_over([stored.image_id]).paths == [stored.path]
    with pytest.raises(ImageAlreadySentError):
        await service.discard(stored.image_id)
    assert stored.image_id in ledger.kept


async def test_handing_over_names_what_the_review_does_not_keep(service: ImageService) -> None:
    """Whether a missing image is a fault is for the caller to say."""
    stored = await service.keep(PNG)

    handover = service.hand_over([stored.image_id, "gone.png"])

    assert handover.paths == [stored.path]
    assert handover.missing == ["gone.png"]


async def test_a_discarded_image_gives_back_its_room(
    service: ImageService, ledger: ImageLedger, store: MemoryImageStore
) -> None:
    stored = await service.keep(PNG)

    await service.discard(stored.image_id)

    assert ledger.held_bytes == 0
    assert service.find(stored.image_id) is None
    assert store.files == {}


async def test_discarding_an_image_never_kept_is_refused(service: ImageService) -> None:
    with pytest.raises(UnknownImageError):
        await service.discard("nothing.png")


class FailingImageStore(MemoryImageStore):
    """A store whose writes never land, the way a shutdown can stop one."""

    async def write(self, name: str, content: bytes) -> Path:
        raise asyncio.CancelledError


async def test_a_write_that_never_lands_gives_back_its_room(ledger: ImageLedger) -> None:
    service = ImageService(FailingImageStore(), ledger)

    with pytest.raises(asyncio.CancelledError):
        await service.keep(PNG)

    assert ledger.held_bytes == 0


async def test_what_is_not_an_image_is_named_so_even_in_a_full_review(
    service: ImageService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reader can fix a wrong format; a full review is a different problem."""
    monkeypatch.setattr(image_service, "MAX_REVIEW_BYTES", 0)

    with pytest.raises(ImageRefusedError) as refused:
        await service.keep(b"not an image at all")

    assert not isinstance(refused.value, ImageTooLargeError)


async def test_an_image_named_twice_is_handed_over_once(service: ImageService) -> None:
    stored = await service.keep(PNG)

    assert service.hand_over([stored.image_id, stored.image_id]).paths == [stored.path]


async def test_requiring_names_the_images_the_review_does_not_keep(service: ImageService, ledger: ImageLedger) -> None:
    stored = await service.keep(PNG)

    with pytest.raises(UnknownImageError, match=r"gone\.png"):
        service.require([stored.image_id, "gone.png"])
    assert ledger.sent == set()

"""Service deciding which pasted images a review keeps, and handing them over.

A screenshot says what a paragraph about a layout cannot. The agent reads
files, not bytes on a wire, so each image is written into the review's
workspace and travels to the agent as a path. What is decided here is only
policy — which formats, how large, how many — and the bookkeeping in the
review's ledger; where the bytes go is the store's business.
"""

import uuid
from pathlib import Path

from pydantic import BaseModel

from claude_review.domain.exceptions import (
    ImageAlreadySentError,
    ImageRefusedError,
    ImageTooLargeError,
    UnknownImageError,
)
from claude_review.domain.models import ImageLedger, StoredImage
from claude_review.domain.protocols import ImageStoreProtocol

BYTES_PER_MEGABYTE = 1024 * 1024

# A whole screen at full resolution fits several times over; anything bigger
# is not a screenshot
MAX_IMAGE_MEGABYTES = 10
MAX_IMAGE_BYTES = MAX_IMAGE_MEGABYTES * BYTES_PER_MEGABYTE

# Everything one review keeps, together. Pasting and removing in a loop would
# otherwise fill whatever disk, or memory, the workspace lives on.
MAX_REVIEW_MEGABYTES = 200
MAX_REVIEW_BYTES = MAX_REVIEW_MEGABYTES * BYTES_PER_MEGABYTE

# More than a handful of images in one thing said — a panel message, a
# comment, a reply — is a gallery, not a question
MAX_IMAGES_PER_MESSAGE = 10


class ImageHandover(BaseModel):
    """The files a set of image ids names, and the ids this review does not keep.

    Which of the two matters is the caller's call: a message written a moment
    ago naming a missing image is a fault, while a thread restored after a
    restart naming one is only a screenshot that did not survive it.
    """

    paths: list[Path]
    missing: list[str]


class ImageMarker(BaseModel):
    """Bytes a file of some format has at a known place."""

    offset: int
    signature: bytes


class ImageFormat(BaseModel):
    """An image format, known by the bytes a file of it carries."""

    extension: str
    media_type: str
    markers: list[ImageMarker]


# What a browser pastes and an agent can read. Recognised by content rather
# than by the type the upload claims, so a file is served back as what it is.
IMAGE_FORMATS = (
    ImageFormat(
        extension=".png",
        media_type="image/png",
        markers=[ImageMarker(offset=0, signature=b"\x89PNG\r\n\x1a\n")],
    ),
    ImageFormat(
        extension=".jpg",
        media_type="image/jpeg",
        markers=[ImageMarker(offset=0, signature=b"\xff\xd8\xff")],
    ),
    ImageFormat(
        extension=".gif",
        media_type="image/gif",
        markers=[ImageMarker(offset=0, signature=b"GIF8")],
    ),
    # A RIFF container that names itself WebP after the length that follows
    ImageFormat(
        extension=".webp",
        media_type="image/webp",
        markers=[ImageMarker(offset=0, signature=b"RIFF"), ImageMarker(offset=8, signature=b"WEBP")],
    ),
)


class ImageService:
    """Keeps, finds, hands over and discards the images of one review."""

    def __init__(self, store: ImageStoreProtocol, ledger: ImageLedger) -> None:
        self._store = store
        self._ledger = ledger

    async def keep(self, content: bytes) -> StoredImage:
        """Write an image into the review's workspace.

        Raises:
            ImageTooLargeError: if the image, or the review with it, is over
                its limit.
            ImageRefusedError: if the content is empty or not in one of the
                formats this review keeps.
        """
        if not content:
            msg = "The upload is empty"
            raise ImageRefusedError(msg)
        size = len(content)
        if size > MAX_IMAGE_BYTES:
            msg = f"The image is over {MAX_IMAGE_MEGABYTES} MB"
            raise ImageTooLargeError(msg)
        image_format = recognise(content)
        if image_format is None:
            accepted = ", ".join(known.extension.lstrip(".") for known in IMAGE_FORMATS)
            msg = f"Not an image this review keeps. It takes: {accepted}"
            raise ImageRefusedError(msg)
        if self._ledger.held_bytes + size > MAX_REVIEW_BYTES:
            msg = f"This review already keeps {MAX_REVIEW_MEGABYTES} MB of images"
            raise ImageTooLargeError(msg)

        # Reserved before the write is awaited, so an upload arriving in the
        # meantime is measured against it
        self._ledger.held_bytes += size
        image_id = f"{uuid.uuid4().hex}{image_format.extension}"
        try:
            path = await self._store.write(image_id, content)
        except BaseException:
            # Whatever stopped the write, a shutdown included, the room it
            # held is given back
            self._ledger.held_bytes -= size
            raise

        stored = StoredImage(image_id=image_id, path=path, media_type=image_format.media_type, size=size)
        self._ledger.kept[image_id] = stored
        return stored

    def find(self, image_id: str) -> StoredImage | None:
        """The image kept under an id, or None if this review keeps none."""
        return self._ledger.kept.get(image_id)

    def require(self, image_ids: list[str]) -> None:
        """Check that this review keeps every one of the images.

        Raises:
            UnknownImageError: naming the ones it does not keep.
        """
        missing = [image_id for image_id in image_ids if image_id not in self._ledger.kept]
        if missing:
            msg = f"No such image in this review: {', '.join(missing)}"
            raise UnknownImageError(msg)

    def hand_over(self, image_ids: list[str]) -> ImageHandover:
        """Name the files the images are, and keep them for the agent.

        Once a path has been given out the agent may open it at any time, so
        every image handed over stays until the review ends.
        """
        # Once each, in the order given: the same image named twice is one file
        unique = list(dict.fromkeys(image_ids))
        kept = [image_id for image_id in unique if image_id in self._ledger.kept]
        self._ledger.sent.update(kept)
        return ImageHandover(
            paths=[self._ledger.kept[image_id].path for image_id in kept],
            missing=[image_id for image_id in unique if image_id not in self._ledger.kept],
        )

    async def discard(self, image_id: str) -> None:
        """Remove an image taken off a message before it was sent.

        Raises:
            UnknownImageError: if this review keeps no such image.
            ImageAlreadySentError: if it went out with a message.
        """
        stored = self._ledger.kept.get(image_id)
        if stored is None:
            msg = f"No such image in this review: {image_id}"
            raise UnknownImageError(msg)
        if image_id in self._ledger.sent:
            msg = "That image was already sent"
            raise ImageAlreadySentError(msg)

        del self._ledger.kept[image_id]
        self._ledger.held_bytes -= stored.size
        await self._store.remove(image_id)


def recognise(content: bytes) -> ImageFormat | None:
    """The format a file is in, read from the bytes it carries."""
    return next((known for known in IMAGE_FORMATS if _carries(content, known)), None)


def _carries(content: bytes, image_format: ImageFormat) -> bool:
    return all(
        content[marker.offset : marker.offset + len(marker.signature)] == marker.signature
        for marker in image_format.markers
    )

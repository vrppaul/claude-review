"""Service deciding which pasted images a review keeps, and handing them over.

A screenshot says what a paragraph about a layout cannot. The agent reads
files, not bytes on a wire, so each image is written into the review's
workspace and travels to the agent as a path. What is decided here is only
policy — which formats, how large, how many — and the bookkeeping of what
the review keeps; where the bytes go is the store's business.
"""

import uuid
from pathlib import Path

import structlog
from pydantic import BaseModel

from claude_review.domain.exceptions import (
    ImageAlreadySentError,
    ImageRefusedError,
    ImagesNotKeptError,
    ImageTooLargeError,
    UnknownImageError,
)
from claude_review.domain.protocols import ImageStoreProtocol

log = structlog.get_logger()

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


class StoredImage(BaseModel):
    """An image the reader pasted, kept where the review's store put it."""

    image_id: str
    path: Path
    media_type: str
    size: int


class ImageQuota(BaseModel):
    """How much one review may keep: each image on its own, and all of them together."""

    image_bytes: int
    review_bytes: int


# What every review is held to
REVIEW_IMAGE_QUOTA = ImageQuota(image_bytes=MAX_IMAGE_BYTES, review_bytes=MAX_REVIEW_BYTES)


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
    """Keeps, finds, hands over and discards the images of one review, for as long as it runs.

    What it keeps is held here rather than read back off the disk: this is
    what says an id exists, so no path is ever built from one, and what keeps
    the review under its limit without counting the directory on every upload.
    """

    def __init__(self, store: ImageStoreProtocol, quota: ImageQuota) -> None:
        self._store = store
        self._quota = quota
        self._kept: dict[str, StoredImage] = {}
        # Images that went out with something said. The agent may still be
        # about to open them, so they stay until the review ends.
        self._sent: set[str] = set()
        # Room taken by uploads still being written, so one arriving in the
        # meantime is measured against them
        self._writing_bytes = 0

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
        if size > self._quota.image_bytes:
            msg = f"The image is over {_in_megabytes(self._quota.image_bytes)}"
            raise ImageTooLargeError(msg)
        image_format = recognise(content)
        if image_format is None:
            accepted = ", ".join(known.extension.lstrip(".") for known in IMAGE_FORMATS)
            msg = f"Not an image this review keeps. It takes: {accepted}"
            raise ImageRefusedError(msg)
        if self._held_bytes() + size > self._quota.review_bytes:
            msg = f"This review already keeps {_in_megabytes(self._quota.review_bytes)} of images"
            raise ImageTooLargeError(msg)

        image_id = f"{uuid.uuid4().hex}{image_format.extension}"
        # Whatever stops the write, a shutdown included, the room it held is given back
        self._writing_bytes += size
        try:
            path = await self._store.write(image_id, content)
        finally:
            self._writing_bytes -= size

        stored = StoredImage(image_id=image_id, path=path, media_type=image_format.media_type, size=size)
        self._kept[image_id] = stored
        return stored

    def find(self, image_id: str) -> StoredImage | None:
        """The image kept under an id, or None if this review keeps none."""
        return self._kept.get(image_id)

    def kept(self, image_id: str) -> StoredImage:
        """The image kept under an id.

        Raises:
            UnknownImageError: if this review keeps no such image.
        """
        stored = self.find(image_id)
        if stored is None:
            msg = f"No such image in this review: {image_id}"
            raise UnknownImageError(msg)
        return stored

    def require(self, image_ids: list[str]) -> None:
        """Check that this review keeps every one of the images.

        Raises:
            ImagesNotKeptError: naming the ones it does not keep.
        """
        missing = [image_id for image_id in image_ids if image_id not in self._kept]
        if missing:
            msg = f"No such image in this review: {', '.join(missing)}"
            raise ImagesNotKeptError(msg)

    def hand_over(self, image_ids: list[str]) -> ImageHandover:
        """Name the files the images are, and keep them for the agent.

        Once a path has been given out the agent may open it at any time, so
        every image handed over stays until the review ends.
        """
        # Once each, in the order given: the same image named twice is one file
        unique = list(dict.fromkeys(image_ids))
        kept = [image_id for image_id in unique if image_id in self._kept]
        self._sent.update(kept)
        return ImageHandover(
            paths=[self._kept[image_id].path for image_id in kept],
            missing=[image_id for image_id in unique if image_id not in self._kept],
        )

    async def discard(self, image_id: str) -> None:
        """Remove an image taken off a message before it was sent.

        Raises:
            UnknownImageError: if this review keeps no such image.
            ImageAlreadySentError: if it went out with a message.
        """
        self.kept(image_id)
        if image_id in self._sent:
            msg = "That image was already sent"
            raise ImageAlreadySentError(msg)

        try:
            await self._store.remove(image_id)
        except OSError as error:
            # Still on the disk, so still kept and counted
            log.warning("image_left_behind", image_id=image_id, reason=str(error))
            return
        del self._kept[image_id]

    def _held_bytes(self) -> int:
        """How much the review keeps, uploads still being written included."""
        return sum(stored.size for stored in self._kept.values()) + self._writing_bytes


def _in_megabytes(byte_count: int) -> str:
    """A limit as the reader is told it, in whole megabytes."""
    return f"{byte_count // BYTES_PER_MEGABYTE} MB"


def recognise(content: bytes) -> ImageFormat | None:
    """The format a file is in, read from the bytes it carries."""
    return next((known for known in IMAGE_FORMATS if _carries(content, known)), None)


def _carries(content: bytes, image_format: ImageFormat) -> bool:
    return all(
        content[marker.offset : marker.offset + len(marker.signature)] == marker.signature
        for marker in image_format.markers
    )

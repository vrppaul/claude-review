"""The directory a review keeps pasted images in."""

import asyncio
from pathlib import Path
from typing import override

from claude_review.domain.interfaces import ImageStore


class DirectoryImageStore(ImageStore):
    """Keeps images as files in one directory of the review's workspace.

    The only place that touches the disk for images. Names come from the
    review, never from the reader, so none can reach outside the directory.
    """

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    @override
    async def write(self, name: str, content: bytes) -> Path:
        path = self._directory / name
        await asyncio.to_thread(path.write_bytes, content)
        return path

    @override
    async def remove(self, name: str) -> None:
        await asyncio.to_thread((self._directory / name).unlink, missing_ok=True)

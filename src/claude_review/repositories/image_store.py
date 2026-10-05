"""The directory a review keeps pasted images in."""

import asyncio
from pathlib import Path


class DirectoryImageStore:
    """Keeps images as files in one directory of the review's workspace.

    The only place that touches the disk for images. Names come from the
    review, never from the reader, so none can reach outside the directory.
    """

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    async def write(self, name: str, content: bytes) -> Path:
        path = self._directory / name
        await asyncio.to_thread(path.write_bytes, content)
        return path

    async def remove(self, name: str) -> None:
        await asyncio.to_thread((self._directory / name).unlink, missing_ok=True)

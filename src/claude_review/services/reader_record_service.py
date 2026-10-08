"""Reading and changing one record of what the review remembers about its reader."""

import asyncio

from pydantic import BaseModel

from claude_review.domain.protocols import RecordStoreProtocol


class ReaderRecordService[Record: BaseModel]:
    """One record about the reader — their settings, or how far they have been shown around."""

    def __init__(self, store: RecordStoreProtocol[Record], record_type: type[Record]) -> None:
        self._store = store
        self._record_type = record_type
        # Two changes at once would each read the record before either wrote,
        # and the second would put back what the first changed
        self._changing = asyncio.Lock()

    async def read(self) -> Record | None:
        """The record as kept, or None for a reader nothing has been kept about."""
        return await self._store.read()

    async def change(self, changes: dict[str, object]) -> Record:
        """Change the fields named and keep the rest, starting from the defaults if nothing was kept.

        Read and written again on every change rather than held in memory:
        another review on the machine may have changed something since.

        Raises:
            ValidationError: if a value is not one the record takes.
        """
        async with self._changing:
            current = await self._store.read() or self._record_type()
            changed = self._record_type.model_validate(current.model_dump() | changes)
            await self._store.write(changed)
            return changed

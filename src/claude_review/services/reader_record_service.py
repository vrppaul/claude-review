"""Reading and changing one record of what the review remembers about its reader."""

import asyncio

from pydantic import BaseModel, ConfigDict

from claude_review.domain.interfaces import RecordChange, RecordStore
from claude_review.domain.models import GuideState, ReaderSettings


class ReaderRecordService[Record: BaseModel]:
    """One record about the reader — their settings, or how far they have been shown around."""

    def __init__(self, store: RecordStore[Record], record_type: type[Record]) -> None:
        self._store = store
        self._record_type = record_type
        # Two changes at once would each read the record before either wrote,
        # and the second would put back what the first changed
        self._changing = asyncio.Lock()

    async def read(self) -> Record | None:
        """The record as kept, or None for a reader nothing has been kept about."""
        return await self._store.read()

    def defaults(self) -> Record:
        """What a reader nothing has been kept about gets."""
        return self._record_type()

    async def change(self, change: RecordChange[Record]) -> Record:
        """Keep the record as a change leaves it, starting from the defaults if nothing was kept.

        Read and written again on every change rather than held in memory:
        another review on the machine may have changed something since.
        """
        async with self._changing:
            current = await self._store.read() or self.defaults()
            changed = change.applied_to(current)
            await self._store.write(changed)
            return changed


class ReaderRecords(BaseModel):
    """Everything a review remembers about its reader: one service for each record, for the review's lifetime.

    One each, so changes arriving together are made one after the other.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    settings: ReaderRecordService[ReaderSettings]
    guide: ReaderRecordService[GuideState]

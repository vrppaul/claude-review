"""What a review keeps of itself while it runs, and what it goes on from as it opens: the one keeper of that record.

A review opened again before its reader finished it goes on as it was
kept. One opened for the first time goes on from its first round, with no
story, and wanting one where the reader has every review's story written as
it opens: the reader's choice is read then, and only then, so a choice made
in a review is one for the next review, never for the one it is made in.
"""

import asyncio

import structlog

from claude_review.domain.interfaces import RecordStore
from claude_review.domain.kept_review import KeptReview
from claude_review.domain.models import FIRST_ROUND, ReaderSettings, StoryWriting
from claude_review.services.reader_record_service import ReaderRecordService

log = structlog.get_logger()


class ReviewRecord:
    """The record a review keeps of itself: read as it opens, written whole then and each time the review moves on.

    A round sent, a story told, asked for or stopped, the diff taken again.
    A round a page says it had reached is the page's to say again.
    """

    def __init__(self, store: RecordStore[KeptReview], *, settings: ReaderRecordService[ReaderSettings]) -> None:
        self._store = store
        # The reader's choices, read as a review opens for the first time
        self._settings = settings
        # Held while the record is written: two writes at once could land in the wrong order, the older last
        self._writing = asyncio.Lock()

    async def opening(self) -> KeptReview:
        """What the review goes on from as it opens: as it was kept, or as a review opened for the first time."""
        return await self._store.read() or await self._first_opening()

    async def keep(self, review: KeptReview) -> None:
        """Keep the review as it now stands, once every write before has landed.

        A review that cannot keep itself still runs: only opening it again
        would lose what it kept.
        """
        async with self._writing:
            try:
                await self._store.write(review)
            except OSError as refusal:
                log.warning("review_not_kept", reason=str(refusal))

    async def _first_opening(self) -> KeptReview:
        """What a review opened for the first time goes on from: its first round, no story, and the reader's choice."""
        settings = await self._settings.read() or self._settings.defaults()
        return KeptReview(
            round=FIRST_ROUND, story=None, story_wanted=settings.story_writing is StoryWriting.AS_THE_REVIEW_OPENS
        )

"""What a review keeps of itself, as its `ReviewRecord` keeps it: a review that cannot keep itself still runs."""

import errno
import os
from typing import override

from pydantic import BaseModel

from claude_review.domain.interfaces import RecordStore
from claude_review.domain.kept_review import KeptReview
from claude_review.domain.models import FIRST_ROUND, ReaderSettings
from claude_review.services.reader_record_service import ReaderRecordService
from claude_review.services.review.review_record import ReviewRecord

# A review in its first round, with no story told
NOTHING_TOLD = KeptReview(round=FIRST_ROUND, story=None, story_wanted=False)


class DiskFull[Record: BaseModel](RecordStore[Record]):
    """Where a record would be kept, on a disk with no room left: nothing was ever written, nothing can be."""

    @override
    async def read(self) -> Record | None:
        return None

    @override
    async def write(self, record: Record) -> None:
        raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))


async def test_a_review_that_cannot_keep_itself_goes_on() -> None:
    """Only opening it again would lose what it kept: the round being sent, or the story told, is not refused over it."""
    record = ReviewRecord(DiskFull(), settings=ReaderRecordService(DiskFull(), ReaderSettings))

    assert await record.keep(NOTHING_TOLD) is None

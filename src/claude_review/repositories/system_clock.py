"""The time as the machine says it, in the unit the review says every time in."""

import time
from typing import override

from claude_review.domain.models import EpochMillis
from claude_review.domain.protocols import Clock

NANOSECONDS_PER_MILLISECOND = 1_000_000


class SystemClock(Clock):
    """What the review reads the time from when nothing stands in for it."""

    @override
    def now(self) -> EpochMillis:
        """The moment now, in epoch milliseconds."""
        return time.time_ns() // NANOSECONDS_PER_MILLISECOND

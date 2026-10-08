"""The time as the machine says it, in the unit the review says every time in."""

import time

NANOSECONDS_PER_MILLISECOND = 1_000_000


class SystemClock:
    """What the review reads the time from when nothing stands in for it."""

    def now(self) -> int:
        """The moment now, in epoch milliseconds."""
        return time.time_ns() // NANOSECONDS_PER_MILLISECOND

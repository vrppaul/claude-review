"""Which round of the review is being written, and the last one sent.

Whoever tags its work with the round, as the content's source tags each
take, is handed the round being written to read (`RoundBeingWritten`), and
never what moves it on.
"""

from abc import ABC, abstractmethod
from typing import override

import structlog

from claude_review.domain.models import FIRST_ROUND, RoundSubmission

log = structlog.get_logger()


class RoundBeingWritten(ABC):
    """Which round of the review is being written, read at the moment it is asked, never changed."""

    @property
    @abstractmethod
    def current(self) -> int:
        """The round being written now."""


class RoundTracker(RoundBeingWritten):
    """The round being written, which goes up each time one is sent and the review stays open."""

    def __init__(self) -> None:
        self._current = FIRST_ROUND
        # The round sent last, which the review writes out as it ends
        self._last_sent: RoundSubmission | None = None

    @property
    @override
    def current(self) -> int:
        return self._current

    @property
    def last_sent(self) -> RoundSubmission | None:
        return self._last_sent

    def catch_up(self, number: int) -> None:
        """Take the round a page says it had got to, never going back.

        A review restarted mid-way comes back believing it is round one, and
        would number the next round wrongly for everyone reading it; a reader
        opening fresh must not drag the review back to the beginning either.
        """
        if number > self._current:
            log.info("round_caught_up", was=self._current, now=number)
            self._current = number

    def sent(self, submission: RoundSubmission) -> None:
        """Remember the round just sent, as the one the review writes out if it ends."""
        self._last_sent = submission

    def begin_next(self) -> int:
        """Begin the next round, and say which it is."""
        self._current += 1
        return self._current

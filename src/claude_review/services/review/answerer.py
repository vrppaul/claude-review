"""The agent answering the review, as the review knows it: whether it is there, what it says of itself, what it does.

The agent lives in another process and is known only by what it says, so
everything here is what it last said — and every page on screen is told the
moment it changes. Whether it is there at all is a lease: renewed by every
call it makes, held while it waits on the review, and lapsing once it has
gone quiet for long enough, so a dead agent does not leave rounds on offer to
nobody.
"""

import asyncio
import contextlib
from collections.abc import Generator

import structlog

from claude_review.domain.interfaces import Clock, PageChannel
from claude_review.domain.models import AgentStatus, AgentWork, FilePath, ProgressStep, says_nothing
from claude_review.domain.page_events import AnswererChanged, StatusReported, WorkReported

log = structlog.get_logger()

# How long the agent counts as there after it last called. Long: it works on a
# round for minutes between two waits, and says nothing while it thinks.
ANSWERER_LEASE_SECONDS = 600.0


class Answerer:
    """Whoever answers the review: there or not, its status, and the work under way."""

    def __init__(self, page: PageChannel, clock: Clock, lease_seconds: float) -> None:
        self._page = page
        self._clock = clock
        self._lease_seconds = lease_seconds
        # Rounds are only worth offering when someone is there to work through them
        self._attached = False
        # How many of the agent's waits on the review are open now
        self._waits = 0
        # When the lease lapses, unless the agent calls again first
        self._lapse: asyncio.TimerHandle | None = None
        # Empty until the agent says anything; a page reloaded mid-conversation
        # reads it back from here
        self._status = AgentStatus()
        # A push is gone once sent, so a page opened or reloaded mid-work is
        # told the work from here
        self._work: AgentWork | None = None

    @property
    def attached(self) -> bool:
        return self._attached

    @property
    def status(self) -> AgentStatus:
        return self._status

    @property
    def work(self) -> AgentWork | None:
        return self._work

    def heard(self) -> None:
        """Note that the agent called: it is there, for another lease from now."""
        self._set_attached(attached=True)
        if self._lapse is not None:
            self._lapse.cancel()
        self._lapse = asyncio.get_running_loop().call_later(self._lease_seconds, self._lease_ran_out)

    @contextlib.contextmanager
    def waiting(self) -> Generator[None]:
        """Hold the lease for as long as the agent waits on the review, and from the end of the wait."""
        self._waits += 1
        self.heard()
        try:
            yield
        finally:
            self._waits -= 1
            self.heard()

    def report_status(self, *, model: str | None, context: str | None) -> None:
        """Take what the agent says about itself; a part it leaves out keeps what it said before."""
        self._status = AgentStatus(
            model=model if model is not None else self._status.model,
            context=context if context is not None else self._status.context,
            at=self._clock.now(),
        )
        self._page.tell(StatusReported(agent=self._status))
        log.info("agent_status", model=self._status.model, context=self._status.context)

    def report_work(
        self, *, message_id: str | None, text: str, files: list[FilePath], steps: list[ProgressStep]
    ) -> None:
        """Say what is being done, replacing whatever was showing; a report of nothing says the work is over."""
        reports_nothing = says_nothing(text) and not steps
        self._set_work(
            None
            if reports_nothing
            else AgentWork(message_id=message_id, text=text, files=files, steps=steps, at=self._clock.now())
        )

    def end_work_for(self, message_id: str | None) -> None:
        """End the work done for one message — answered, or taken back — and nothing else."""
        if self._work is not None and message_id is not None and self._work.message_id == message_id:
            self._set_work(None)

    def message_arrived(self) -> None:
        """Note a new message: whatever was being done for the last one is history."""
        if self._work is not None:
            self._set_work(None)

    def _lease_ran_out(self) -> None:
        self._lapse = None
        if self._waits == 0:
            self._set_attached(attached=False)

    def _set_attached(self, *, attached: bool) -> None:
        """Say whether the agent is there, and tell the pages when that changes."""
        if attached == self._attached:
            return
        self._attached = attached
        self._page.tell(AnswererChanged(attached=attached))
        log.info("answerer_changed", attached=attached)

    def _set_work(self, work: AgentWork | None) -> None:
        self._work = work
        self._page.tell(WorkReported(work=work))

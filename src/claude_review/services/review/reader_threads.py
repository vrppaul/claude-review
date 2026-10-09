"""The threads the reader's page holds, and the ids the agent's own threads take beside them.

The threads are the reader's unsent work and live in their page; an agent
that attaches later has no other way to learn they exist. They are kept as
the page said them, images by their ids: they are handed over only to an
agent that reads them, so an image in a comment nobody has read yet can
still be taken off.
"""

import structlog

from claude_review.domain.exceptions import UnknownThreadError
from claude_review.domain.models import ThreadDraft

log = structlog.get_logger()

# How the threads the agent raises are named, apart from the page's own
RAISED_PREFIX = "raised-"


class ReaderThreads:
    """What the page last said it holds, and the numbering of the threads the agent raises."""

    def __init__(self) -> None:
        self._held: list[ThreadDraft] = []
        # The ids of threads the page holds that this review could not read
        self._unreadable_ids: list[str] = []
        # Threads the agent has raised. Numbered apart from the reader's,
        # whose ids are minted in the page, so the two cannot collide.
        self._raised = 0

    @property
    def held(self) -> list[ThreadDraft]:
        """The threads as the page last described them; a copy."""
        return list(self._held)

    def find(self, thread_id: str) -> ThreadDraft:
        """One thread the page holds.

        Raises:
            UnknownThreadError: if it holds none by that id.
        """
        held = next((thread for thread in self._held if thread.thread_id == thread_id), None)
        if held is None:
            msg = f"No thread {thread_id} in this review"
            raise UnknownThreadError(msg)
        return held

    def hold(self, readable: list[ThreadDraft], unreadable_ids: list[str]) -> None:
        """Take the threads the page holds, and never hand out an id one of them has.

        A review restarted mid-way starts counting again from nothing, while
        the page still holds the threads the agent raised before — the ones
        this review could not read included.
        """
        self._held = readable
        held_ids = [*(thread.thread_id for thread in readable), *unreadable_ids]
        self._raised = max([self._raised, *(_raised_number(thread_id) for thread_id in held_ids)])
        # Said when it changes rather than on every hello, which comes as
        # often as once a second while the reader types
        if unreadable_ids != self._unreadable_ids:
            log.warning("threads_left_out", thread_ids=unreadable_ids)
        self._unreadable_ids = unreadable_ids

    def raise_id(self) -> str:
        """The id of the next thread the agent raises."""
        self._raised += 1
        return f"{RAISED_PREFIX}{self._raised}"


def _raised_number(thread_id: str) -> int:
    """The number in an id this review handed out, or 0 for any other id."""
    number = thread_id.removeprefix(RAISED_PREFIX)
    return int(number) if thread_id.startswith(RAISED_PREFIX) and number.isdigit() else 0

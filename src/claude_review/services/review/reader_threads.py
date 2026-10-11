"""The threads the reader's page holds, and the ids the agent's own threads take beside them.

The threads are the reader's unsent work and live in their page; an agent
that attaches later has no other way to learn they exist. They are kept as
the page said them, images by their ids: they are handed over only to an
agent that reads them, so an image in a comment nobody has read yet can
still be taken off.

The agent's own threads are held from the moment they are raised, and a
page that says what it holds updates them but never takes them away: a
page with no draft of the review — another browser, a private window —
holds none, and the agent's threads must outlive it. A page opening with
no draft reads them all from here.
"""

import structlog

from claude_review.domain.exceptions import UnknownThreadError
from claude_review.domain.models import ThreadDraft, TurnAuthor

log = structlog.get_logger()

# How the threads the agent raises are named, apart from the page's own
RAISED_PREFIX = "raised-"


class ReaderThreads:
    """What the page last said it holds, the threads the agent has had, and the numbering of those it raises."""

    def __init__(self) -> None:
        self._held: list[ThreadDraft] = []
        # The ids of threads the page holds that this review could not read
        self._unreadable_ids: list[str] = []
        # Threads the agent has raised. Numbered apart from the reader's,
        # whose ids are minted in the page, so the two cannot collide.
        self._raised = 0
        # The ids of threads the agent was handed or raised. It may answer in
        # one before the page says it holds it: a page says so at most once a
        # second, and of several tabs on the review, the last to say it wins.
        self._known_to_the_agent: set[str] = set()

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
            raise _unknown(thread_id)
        return held

    def require(self, thread_id: str) -> None:
        """Refuse a thread this review never heard of: no page holds it, so nothing said in it would be shown.

        Raises:
            UnknownThreadError: if the page does not say it holds the thread,
                and the agent was neither handed it nor raised it.
        """
        held_ids = {thread.thread_id for thread in self._held}
        if thread_id not in held_ids | set(self._unreadable_ids) | self._known_to_the_agent:
            raise _unknown(thread_id)

    def handed(self, thread_id: str) -> None:
        """Note a thread the agent was handed, which it may answer in from now on."""
        self._known_to_the_agent.add(thread_id)

    def hold(self, readable: list[ThreadDraft], unreadable_ids: list[str]) -> None:
        """Take the threads the page holds, keep the agent's own it leaves out, and never hand out an id one has.

        A review restarted mid-way starts counting again from nothing, while
        the page still holds the threads the agent raised before — the ones
        this review could not read included.
        """
        said_ids = {*(thread.thread_id for thread in readable), *unreadable_ids}
        left_out = [thread for thread in self._held if _is_raised(thread) and thread.thread_id not in said_ids]
        self._held = [*readable, *left_out]
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
        raised = f"{RAISED_PREFIX}{self._raised}"
        self._known_to_the_agent.add(raised)
        return raised

    def raised(self, thread: ThreadDraft) -> None:
        """Hold a thread the agent raised, as it was raised, until a page says what became of it."""
        self._held = [*self._held, thread]


def _unknown(thread_id: str) -> UnknownThreadError:
    """What a thread named and not held is refused with."""
    msg = f"No thread {thread_id} in this review"
    return UnknownThreadError(msg)


def _is_raised(thread: ThreadDraft) -> bool:
    """Whether the agent raised the thread, rather than the reader writing it."""
    return thread.raised_by == TurnAuthor.AUTHOR


def _raised_number(thread_id: str) -> int:
    """The number in an id this review handed out, or 0 for any other id."""
    number = thread_id.removeprefix(RAISED_PREFIX)
    return int(number) if thread_id.startswith(RAISED_PREFIX) and number.isdigit() else 0

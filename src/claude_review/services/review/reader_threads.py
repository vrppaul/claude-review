"""The threads the reader's page holds, and the agent's own beside them: their ids, and what the agent has of each.

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

What the agent has of a thread — what it raised it with, what it was
handed — stays as it first had it, and only grows: a thread handed over
again adds what was said since, and a copy older than one handed before
takes nothing away. A thread that comes back changed in it is refused.
The reader says more after it; they never rewrite it. It keeps the round
the agent first had the thread in, and whether the thread was settled when
the agent was last handed it, so a page can tell what still goes to it.
"""

import re

import structlog

from claude_review.domain.exceptions import HandedWordsChangedError, UnknownThreadError
from claude_review.domain.models import SaidAsHanded, ThreadAsHanded, ThreadDraft, TurnAuthor

log = structlog.get_logger()

# How the threads the agent raises are named, apart from the page's own: the
# prefix, then their number in plain digits
RAISED_PREFIX = "raised-"
RAISED_NUMBER = re.compile(r"[0-9]+")


class ReaderThreads:
    """What the page last said it holds, what the agent has of each thread, and the numbering of those it raises."""

    def __init__(self) -> None:
        self._held: list[ThreadDraft] = []
        # The ids of threads the page holds that this review could not read
        self._unreadable_ids: list[str] = []
        # How many threads the page holds of which not even an id could be read
        self._unnamed_count = 0
        # Threads the agent has raised. Numbered apart from the reader's,
        # whose ids are minted in the page, so the two cannot collide.
        self._raised = 0
        # What the agent has of each thread it raised or was handed, by
        # thread. It may answer in one before the page says it holds it: a
        # page says so at most once a second, and of several tabs on the
        # review, the last to say it wins. One it had before a restart is not
        # here, and nothing can be said of it.
        self._handed: dict[str, ThreadAsHanded] = {}

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
        if thread_id not in held_ids | set(self._unreadable_ids) | self._handed.keys():
            raise _unknown(thread_id)

    def handed(self, thread: ThreadDraft, *, round_number: int) -> ThreadAsHanded:
        """Note a thread the agent was handed in this round, which it may answer in from now on; say what it now has
        of it.

        Added to what it had: a turn it has keeps the words it first had, and
        one a copy no longer holds stays.
        """
        had = self._handed.get(thread.thread_id)
        has = _as_handed(thread, round_number) if had is None else had.grown_by(thread)
        self._handed[thread.thread_id] = has
        return has

    def handed_over(self) -> dict[str, ThreadAsHanded]:
        """What the agent has of each thread it raised or was handed, by thread."""
        return dict(self._handed)

    def hold(self, readable: list[ThreadDraft], unreadable_ids: list[str], *, unnamed_count: int) -> None:
        """Take the threads the page holds, keep the agent's own it leaves out, and never hand out an id one has.

        A review restarted mid-way starts counting again from nothing, while
        the page still holds the threads the agent raised before — the ones
        this review could not read included. Of those, the ones whose id it
        could read are held by it; of the rest, only how many there are.
        """
        said_ids = {*(thread.thread_id for thread in readable), *unreadable_ids}
        left_out = [thread for thread in self._held if _is_raised(thread) and thread.thread_id not in said_ids]
        self._held = [*readable, *left_out]
        held_ids = [*(thread.thread_id for thread in readable), *unreadable_ids]
        self._raised = max([self._raised, *(_raised_number(thread_id) for thread_id in held_ids)])
        # Said when it changes rather than on every hello, which comes as
        # often as once a second while the reader types
        if unreadable_ids != self._unreadable_ids or unnamed_count != self._unnamed_count:
            log.warning("threads_left_out", thread_ids=unreadable_ids, unnamed_count=unnamed_count)
        self._unreadable_ids = unreadable_ids
        self._unnamed_count = unnamed_count

    def raise_id(self) -> str:
        """The id of the next thread the agent raises."""
        self._raised += 1
        return f"{RAISED_PREFIX}{self._raised}"

    def raised(self, thread: ThreadDraft, *, round_number: int) -> ThreadAsHanded:
        """Hold a thread the agent raised in this round, until a page says what became of it; say what the agent has
        of it."""
        self._held = [*self._held, thread]
        has = _as_handed(thread, round_number)
        self._handed[thread.thread_id] = has
        return has

    def check_handed(self, threads: list[ThreadDraft]) -> None:
        """Refuse a thread changed in what the agent has of it.

        Raises:
            HandedWordsChangedError: if one of them is.
        """
        for thread in threads:
            as_handed = self._handed.get(thread.thread_id)
            if as_handed is not None and not as_handed.kept_in(thread):
                msg = f"{thread.thread_id} changes what the agent has of it, which stays as the agent has it"
                raise HandedWordsChangedError(msg)


def _as_handed(thread: ThreadDraft, round_number: int) -> ThreadAsHanded:
    """What the agent has of a thread the first time it is handed it, or raises it, in a round: all of it."""
    return ThreadAsHanded(
        severity=thread.severity,
        opening=SaidAsHanded(author=thread.raised_by, body=thread.body, images=thread.images),
        turns=thread.turns,
        round=round_number,
        resolved=thread.resolved,
    )


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
    return int(number) if thread_id.startswith(RAISED_PREFIX) and RAISED_NUMBER.fullmatch(number) else 0

"""Shared server state for the review session."""

import asyncio

import structlog

from claude_review.domain.models import (
    AgentStatus,
    ImageLedger,
    PanelEntry,
    RoundSubmission,
    TreeSnapshot,
    TreeState,
)
from claude_review.presentation.schemas import (
    AgentWork,
    AnswererPush,
    HeldThreads,
    ProgressPush,
    ServerPush,
    ThreadInput,
)
from claude_review.services.agent_inbox import AgentInbox

log = structlog.get_logger()

# How the threads the author raises are named, apart from the browser's own
RAISED_PREFIX = "raised-"


class ServerState:
    """Shared mutable state between the HTTP server and the CLI event loop.

    The browser holds a socket open for as long as the review is on screen,
    which is how the server knows to stay up. A poll could not do this: a
    background tab has its timers throttled to about once a minute, so a
    review left open in another tab looked abandoned and the server exited
    from under it. A socket is not throttled.
    """

    def __init__(self, shutdown_event: asyncio.Event) -> None:
        self.shutdown_event = shutdown_event
        # The round sent last, which the review writes out as it ends
        self.last_round: RoundSubmission | None = None
        self._open_sockets = 0
        self._ever_connected = False
        self._alone_since: float | None = None
        # One queue per open review, of pushes already written as the JSON
        # the socket sends
        self._listeners: set[asyncio.Queue[str]] = set()
        # What the reader has handed over and nobody has taken yet: questions
        # about a thread, rounds of the review itself, and what was typed in
        # the panel. Read out once the review is over, too, until nothing is left.
        self.inbox = AgentInbox(closed=shutdown_event)
        # Which round is being written. It goes up when one is sent and the
        # review stays open.
        self.round = 1
        # Whether anything is waiting to answer. Rounds are only worth
        # offering when someone is there to work through them.
        self.answerer_attached = False
        # What the agent has said about itself. Empty until it says anything;
        # a review reloaded mid-conversation reads it back from here.
        self.agent = AgentStatus()
        # What the agent is doing right now, if anything. A push is gone once
        # sent, so a review opened or reloaded mid-work is told it from here.
        self._work: AgentWork | None = None
        # The working tree as it stood when the diff on screen was taken. The
        # watcher compares against this, so retaking the diff is what settles it.
        self.tree: TreeState = frozenset()
        # Threads the author has raised. Numbered apart from the reader's,
        # whose ids are minted in the browser, so the two cannot collide.
        self._raised = 0
        # What the review holds, as the browser last described it. The
        # threads are the reader's unsent work and live in their browser; an
        # agent that attaches later has no other way to learn they exist.
        # Kept as the browser said them, images by their ids: they are handed
        # over only to an agent that reads them, so an image in a comment
        # nobody has read yet can still be taken off.
        self.threads: list[ThreadInput] = []
        # The ids of threads the browser holds that this server could not read
        self._unreadable_ids: list[str] = []
        # What has been said in the panel, both halves, in order
        self.panel: list[PanelEntry] = []
        # The tree behind every diff this review has taken, oldest first. The
        # last one is what is on screen; the first of each round is a base
        # the reader can go back to.
        self.snapshots: list[TreeSnapshot] = []
        # The images pasted into the panel: which exist, which went out with
        # a message, and how much they weigh together
        self.images = ImageLedger()
        # Held while the diff is taken again, so two retakes never interleave
        self.retaking = asyncio.Lock()

    def raise_id(self) -> str:
        """The id of the next thread the author raises."""
        self._raised += 1
        return f"{RAISED_PREFIX}{self._raised}"

    def hold_threads(self, held: HeldThreads) -> None:
        """Take the threads the browser holds, and never hand out an id one of them has.

        A server restarted mid-review starts counting again from nothing, while
        the browser still holds the threads the author raised before it — the
        ones this server could not read included.
        """
        self.threads = held.readable
        held_ids = [*(thread.thread_id for thread in held.readable), *held.unreadable_ids]
        self._raised = max([self._raised, *(_raised_number(thread_id) for thread_id in held_ids)])
        # Said when it changes rather than on every hello, which comes as
        # often as once a second while the reader types
        if held.unreadable_ids != self._unreadable_ids:
            log.warning("threads_left_out", thread_ids=held.unreadable_ids)
        self._unreadable_ids = held.unreadable_ids

    def connected(self, now: float) -> None:
        self._open_sockets += 1
        self._ever_connected = True
        self._alone_since = None

    def disconnected(self, now: float) -> None:
        self._open_sockets = max(0, self._open_sockets - 1)
        if self._open_sockets == 0:
            self._alone_since = now

    def browser_gone(self, now: float, grace: float) -> bool:
        """Whether the review has been closed rather than merely reloaded.

        A reload drops the socket and takes it again within a moment, so a
        gap shorter than the grace period is not the reader leaving.
        """
        if not self._ever_connected or self._alone_since is None:
            return False
        return now - self._alone_since > grace

    def attach_answerer(self) -> None:
        """Note that something is waiting to answer, and tell the review."""
        if self.answerer_attached:
            return
        self.answerer_attached = True
        self.push(AnswererPush(attached=True))

    def report_work(self, work: AgentWork | None) -> None:
        """Say what the agent is doing, or that it is done, to every review open now and every one opened later."""
        self._work = work
        self.push(ProgressPush(work=work))

    def end_work_for(self, message_id: str | None) -> None:
        """End the work done for one message — answered, or taken back — and nothing else."""
        if self._work is not None and message_id is not None and self._work.message_id == message_id:
            self.report_work(None)

    def message_arrived(self) -> None:
        """Note a new message: whatever was being done for the last one is history."""
        if self._work is not None:
            self.report_work(None)

    def listen(self) -> asyncio.Queue[str]:
        """Register a socket to receive what the server pushes, starting with the work under way."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        if self._work is not None:
            queue.put_nowait(ProgressPush(work=self._work).model_dump_json())
        self._listeners.add(queue)
        return queue

    def stop_listening(self, queue: asyncio.Queue[str]) -> None:
        self._listeners.discard(queue)

    def push(self, push: ServerPush) -> None:
        """Send a push to every open review, written down once, as it stands now.

        Written before it is queued, so every review is sent the same words,
        and nothing that changes after — the agent's work reported again, a
        status replaced — reaches a push still waiting in a queue.
        """
        said = push.model_dump_json()
        for queue in self._listeners:
            queue.put_nowait(said)


def _raised_number(thread_id: str) -> int:
    """The number in an id this server handed out, or 0 for any other id."""
    number = thread_id.removeprefix(RAISED_PREFIX)
    return int(number) if thread_id.startswith(RAISED_PREFIX) and number.isdigit() else 0

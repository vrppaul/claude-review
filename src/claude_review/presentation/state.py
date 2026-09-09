"""Shared server state for the review session."""

import asyncio


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
        self.result: str | None = None
        self._open_sockets = 0
        self._ever_connected = False
        self._alone_since: float | None = None
        self._listeners: set[asyncio.Queue[dict]] = set()

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

    def listen(self) -> asyncio.Queue[dict]:
        """Register a socket to receive what the server pushes."""
        queue: asyncio.Queue[dict] = asyncio.Queue()
        self._listeners.add(queue)
        return queue

    def stop_listening(self, queue: asyncio.Queue[dict]) -> None:
        self._listeners.discard(queue)

    def push(self, message: dict) -> None:
        """Send a message to every open review."""
        for queue in self._listeners:
            queue.put_nowait(message)

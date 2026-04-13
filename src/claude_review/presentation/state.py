"""Shared server state for the review session."""

import asyncio


class ServerState:
    """Shared mutable state between the HTTP server and the CLI event loop."""

    def __init__(self, shutdown_event: asyncio.Event) -> None:
        self.shutdown_event = shutdown_event
        self.result: str | None = None
        self.last_heartbeat: float | None = None

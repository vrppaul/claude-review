"""The server one review runs on: uvicorn, ending with the review and leaving the signals to it."""

import asyncio
import contextlib
import socket
from collections.abc import Generator

import uvicorn
from fastapi import FastAPI

from claude_review.services.review_lifetime import EndReason, ReviewLifetime

# Only what goes wrong: a review is quiet by design
SERVER_LOG_LEVEL = "error"
# The default picks uvicorn's older websockets integration, which warns on
# every connection with websockets 14 and later
WEBSOCKETS_IMPLEMENTATION = "websockets-sansio"
# How long the requests still running when the review ends may take to
# finish. An agent's wait ends with the review at once; nothing else should
# take this long, and a review must not hang on its way out.
GRACEFUL_SHUTDOWN_SECONDS = 5


class ServerStartError(Exception):
    """Raised when the review's server stopped before it ever listened."""


class ReviewServer(uvicorn.Server):
    """uvicorn serving one review, for as long as the review runs.

    It stops once the review has ended, whatever ended it, and ends the
    review if it stops first. It leaves the signals alone: uvicorn raises a
    signal it caught again once it has stopped, with the default handler back
    in place, and that ends the process before the review's own way out has
    run — its directories are left behind and the last round is never printed.
    """

    def __init__(self, app: FastAPI, lifetime: ReviewLifetime) -> None:
        super().__init__(
            uvicorn.Config(
                app,
                log_level=SERVER_LOG_LEVEL,
                ws=WEBSOCKETS_IMPLEMENTATION,
                timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_SECONDS,
            )
        )
        self._lifetime = lifetime
        # Whether it came up: settled once it listens, or once it stops without ever listening
        self._came_up: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        # What stopped it before it ever listened, when something was raised
        self._start_failure: Exception | None = None

    async def serve_until_ended(self, listening: socket.socket) -> None:
        """Serve on the socket until the review ends, and end the review if serving stops first.

        A failure before the server listens is kept, for `raise_if_it_never_came_up`
        to explain, rather than raised among the other things the review runs; one
        once it listens is a fault, and is raised as it is.
        """
        try:
            await self.serve(sockets=[listening])
        except Exception as failure:
            if self.started:
                raise
            self._start_failure = failure
        finally:
            if not self._came_up.done():
                self._came_up.set_result(False)
            self._lifetime.end(EndReason.SERVER_STOPPED)

    def raise_if_it_never_came_up(self) -> None:
        """Raise `ServerStartError` if the server stopped before it ever listened, with why when it said.

        Raises:
            ServerStartError: If the server never listened.
        """
        if not self.started:
            msg = "the review's server stopped before it started listening"
            if self._start_failure is not None:
                msg = f"{msg}: {self._start_failure}"
            raise ServerStartError(msg) from self._start_failure

    async def came_up(self) -> bool:
        """Wait until the server listens, or stops without ever listening, and say which."""
        return await asyncio.shield(self._came_up)

    async def startup(self, sockets: list[socket.socket] | None = None) -> None:
        await super().startup(sockets=sockets)
        if self.started:
            self._came_up.set_result(True)

    async def on_tick(self, counter: int) -> bool:
        return await super().on_tick(counter) or self._lifetime.has_ended

    @contextlib.contextmanager
    def capture_signals(self) -> Generator[None]:
        yield

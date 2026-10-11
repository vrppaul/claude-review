"""A review's session socket held as a browser holds it, over a real connection.

Spoken with wsproto, the library the review's own server speaks it with.
Starlette's test client fakes the socket inside the process; these are for
the tests about the server that really runs.
"""

import asyncio
import contextlib
import socket
import time
from collections import deque
from collections.abc import AsyncGenerator
from typing import Self, override

from wsproto import ConnectionType, WSConnection
from wsproto.connection import ConnectionState
from wsproto.events import CloseConnection, Event, Ping, RejectConnection, Request, TextMessage
from wsproto.frame_protocol import CloseReason

from tests.helpers import LOOPBACK, SESSION_ROUTE, PushSource

# How much is taken off the connection at a time
READ_BYTES = 65536
# How long connecting and the handshake may take together
HANDSHAKE_SECONDS = 10.0
# How long one message, or the goodbye, may take to go out
SEND_SECONDS = 10.0
ORIGIN_HEADER = b"Origin"


class HandshakeRefusedError(Exception):
    """The review answered the handshake with a refusal rather than a socket."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"the handshake was refused with {status_code}")
        self.status_code = status_code


class PageSocket(PushSource):
    """A page's session socket: what the review pushes is read off it, what the page says is sent on it."""

    def __init__(self, port: int, *, origin: str | None = None, receive_buffer: int | None = None) -> None:
        """Open the session socket of the review serving on `port`, once the review has answered the handshake.

        Without an origin it arrives as from no page at all. A receive buffer
        holds the page's side of the connection to that little, so whatever a
        page that stops reading is sent backs up on the review's side.

        Raises:
            HandshakeRefusedError: if the review refuses the socket.
        """
        self._connection = socket.socket()
        self._protocol = WSConnection(ConnectionType.CLIENT)
        # Messages read off the connection and not yet asked for
        self._received: deque[str] = deque()
        # The text of a message whose last frame has not arrived yet
        self._unfinished = ""
        # The code the review closed the socket with, once it has
        self._closed_with: int | None = None
        if receive_buffer is not None:
            self._connection.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, receive_buffer)
        try:
            self._shake_hands(port, origin)
        except BaseException:
            self._connection.close()
            raise

    @property
    def is_open(self) -> bool:
        return self._protocol.state == ConnectionState.OPEN

    @property
    def closed_with(self) -> int | None:
        """The code the review closed the socket with, once it has."""
        return self._closed_with

    def send(self, text: str) -> None:
        self._send_event(TextMessage(data=text))

    @override
    def receive(self, *, timeout: float) -> str:
        """The next message the review sends, within `timeout` seconds.

        Raises:
            TimeoutError: if none arrives in time.
            ConnectionError: if the review has closed the socket and sent nothing more before it.
        """
        deadline = time.monotonic() + timeout
        while not self._received:
            if self._closed_with is not None:
                failure = f"the review closed the socket with {self._closed_with}"
                raise ConnectionError(failure)
            self._read(deadline)
        return self._received.popleft()

    def close(self) -> None:
        """Go as a page does: say so, then hang up, whatever became of saying so.

        A review that has already let the page go hung up first, and there is
        nobody left to tell.
        """
        try:
            with contextlib.suppress(OSError):
                if self.is_open:
                    self._send_event(CloseConnection(code=CloseReason.NORMAL_CLOSURE))
        finally:
            self._connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *raised: object) -> None:
        # Closed whether or not the block raised: what it raised goes on up
        self.close()

    def _shake_hands(self, port: int, origin: str | None) -> None:
        deadline = time.monotonic() + HANDSHAKE_SECONDS
        self._connection.settimeout(HANDSHAKE_SECONDS)
        self._connection.connect((LOOPBACK, port))
        headers = [(ORIGIN_HEADER, origin.encode())] if origin is not None else []
        self._send_event(Request(host=f"{LOOPBACK}:{port}", target=SESSION_ROUTE, extra_headers=headers))
        # The review's acceptance shows as the connection opening
        while self._protocol.state == ConnectionState.CONNECTING:
            self._read(deadline)

    def _read(self, deadline: float) -> None:
        """Take what arrives next off the connection, by `deadline` at the latest."""
        self._connection.settimeout(_seconds_left(deadline))
        data = self._connection.recv(READ_BYTES)
        if not data:
            failure = "the review closed the connection"
            raise ConnectionError(failure)
        self._protocol.receive_data(data)
        for event in self._protocol.events():
            match event:
                case RejectConnection():
                    raise HandshakeRefusedError(event.status_code)
                case TextMessage():
                    self._take_text(event)
                case Ping():
                    self._send_event(event.response())
                case CloseConnection():
                    # Answered, as the protocol asks, unless the review hung up
                    # straight after; what arrived before it is still read
                    with contextlib.suppress(OSError):
                        self._send_event(event.response())
                    self._closed_with = event.code
                case _:
                    # The acceptance is read off the state; nothing else is for a page
                    pass

    def _send_event(self, event: Event) -> None:
        """Send one event, under a timeout of its own rather than whatever the last read left."""
        self._connection.settimeout(SEND_SECONDS)
        self._connection.sendall(self._protocol.send(event))

    def _take_text(self, frame: TextMessage) -> None:
        self._unfinished += frame.data
        if frame.message_finished:
            self._received.append(self._unfinished)
            self._unfinished = ""


@contextlib.asynccontextmanager
async def page_socket_held(port: int, *, receive_buffer: int | None = None) -> AsyncGenerator[PageSocket]:
    """The session socket, held open by a test that runs on the review's own event loop.

    The handshake waits for the server, and the server answers on this very
    loop: opened on a thread of its own, the socket leaves the loop free to
    answer it.
    """
    page = await asyncio.to_thread(PageSocket, port, receive_buffer=receive_buffer)
    with page:
        yield page


def _seconds_left(deadline: float) -> float:
    """How long is left until `deadline`.

    Raises:
        TimeoutError: if it has passed.
    """
    left = deadline - time.monotonic()
    if left <= 0:
        failure = "nothing arrived in time"
        raise TimeoutError(failure)
    return left

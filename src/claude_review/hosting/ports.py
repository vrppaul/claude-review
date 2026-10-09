"""Which port a review listens on: the one asked for, or one worked out from what it reviews."""

import hashlib
import socket

import structlog

from claude_review.domain.exceptions import PortUnavailableError
from claude_review.hosting.address import LOOPBACK

log = structlog.get_logger()

# Where derived ports live: above the well-known and registered services,
# below the ephemeral range the kernel hands out
STABLE_PORT_FLOOR = 40_000
STABLE_PORT_CEILING = 60_000
# How much of a review's digest becomes its port
PORT_DIGEST_BYTES = 4

# The port that asks the kernel for any free one
ANY_FREE_PORT = 0
# The ports a review can be found on
LOWEST_PORT = 1
HIGHEST_PORT = 65_535


def stable_port(identity: str) -> int:
    """Work out which port this review should come back on.

    A review reopened on the same thing should land on the same origin: an
    unsent draft lives in the browser's storage, which is keyed by origin,
    so a fresh port every time throws away the comments of whoever closed
    the tab and opened the review again. The identity says what "the same
    thing" is.
    """
    span = STABLE_PORT_CEILING - STABLE_PORT_FLOOR
    digest = hashlib.blake2s(identity.encode(), digest_size=PORT_DIGEST_BYTES).digest()
    return STABLE_PORT_FLOOR + int.from_bytes(digest) % span


def bind(port: int, *, may_fall_back: bool) -> socket.socket:
    """Take the loopback port the server will listen on.

    Taken here rather than by uvicorn: a port already in use then surfaces
    as an error that can be explained, instead of uvicorn calling sys.exit()
    from inside the event loop.

    Raises:
        PortUnavailableError: If a port that was asked for is already taken.
    """
    listening = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listening.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listening.bind((LOOPBACK, port))
    except OSError as error:
        listening.close()
        if may_fall_back:
            # Nobody asked for this port; it was worked out from what is
            # being reviewed. Something else holding it is not the reader's
            # problem, and a review on any port beats no review.
            log.info("derived_port_taken", port=port)
            return bind(ANY_FREE_PORT, may_fall_back=False)
        msg = f"port {port} is already in use — pass a different --port, or omit it to pick a free one"
        raise PortUnavailableError(msg) from error
    listening.listen(socket.SOMAXCONN)
    return listening

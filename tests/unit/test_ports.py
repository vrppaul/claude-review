"""Which port a review listens on: the same one each time it is opened on the same thing."""

import socket
from collections.abc import Iterator

import pytest

from claude_review.domain.exceptions import PortUnavailableError
from claude_review.hosting.address import LOOPBACK
from claude_review.hosting.ports import ANY_FREE_PORT, STABLE_PORT_CEILING, STABLE_PORT_FLOOR, bind, stable_port

A_REVIEW = "/home/dev/project\nHEAD~3"
ANOTHER_REVIEW = "/home/dev/other\nHEAD~3"


@pytest.fixture
def taken_port() -> Iterator[int]:
    """A port something else is listening on."""
    with socket.socket() as holder:
        holder.bind((LOOPBACK, ANY_FREE_PORT))
        holder.listen()
        yield holder.getsockname()[1]


def test_reopening_the_same_review_lands_on_the_same_port() -> None:
    """The port is the origin, and the origin is where a draft is kept."""
    assert stable_port(A_REVIEW) == stable_port(A_REVIEW)


def test_a_different_review_gets_a_different_port() -> None:
    """Two repositories reopened side by side must not share a draft."""
    assert stable_port(A_REVIEW) != stable_port(ANOTHER_REVIEW)


def test_a_derived_port_stays_out_of_the_way() -> None:
    """High enough to be free of well-known services, low enough to be free of ephemeral ports."""
    assert STABLE_PORT_FLOOR <= stable_port(A_REVIEW) < STABLE_PORT_CEILING


def test_a_derived_port_already_taken_gives_way_to_a_free_one(taken_port: int) -> None:
    """Nobody asked for that port, and a review on any port beats no review."""
    listening = bind(taken_port, may_fall_back=True)

    assert listening.getsockname()[1] != taken_port
    listening.close()


def test_a_port_asked_for_and_already_taken_is_refused(taken_port: int) -> None:
    """Somebody asked for that one, and moving them elsewhere would hide it."""
    with pytest.raises(PortUnavailableError, match=str(taken_port)):
        bind(taken_port, may_fall_back=False)

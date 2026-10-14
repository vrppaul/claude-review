"""How what the review tells its pages is delivered down the session socket.

Every connection starts with a welcome. Then each push arrives in a
numbered delivery, numbered across the whole run of the review: a page
that drops its socket — a laptop asleep, a network gone — comes back
saying which run it was reading and the last number it had, and is handed
whatever it missed, as long as the review still keeps it. One that cannot
be handed all of it is told so, and learns again from the review's facts
what the pushes would have said.

The pushes say what happened; this says how they reached the page.
"""

from enum import StrEnum, auto
from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from claude_review.domain.models import MAX_ID_LENGTH
from claude_review.presentation.wire.base import WireBool, WireModel
from claude_review.presentation.wire.pushes import ServerPush


class SessionMessageKind(StrEnum):
    """What the server says down the session socket, as the `type` the browser reads.

    WELCOME — the first thing said on every connection.
    DELIVERY — one push, numbered.
    """

    WELCOME = auto()
    DELIVERY = auto()


class Welcome(WireModel):
    """Which review, and which run of it, the page reached; how far its telling has got; whether it missed nothing.

    `identity` names the review as GET /api/review does: another review may
    answer on the same port once this one is over, and a page must know it
    is not its own before it says anything to it. `sequence` is the number
    of the last push told before this connection. A page handed what it
    missed reads on from its own last number; one that was not reads on
    from here.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal[SessionMessageKind.WELCOME] = SessionMessageKind.WELCOME
    identity: str
    instance: str
    sequence: int
    resumed: WireBool


class Delivery(WireModel):
    """One push, with its number in the review's telling."""

    model_config = ConfigDict(frozen=True)

    type: Literal[SessionMessageKind.DELIVERY] = SessionMessageKind.DELIVERY
    sequence: int
    push: ServerPush


# What the server says down the session socket, told apart by `type`
type SessionMessage = Annotated[Welcome | Delivery, Field(discriminator="type")]


# A review, as a page names the one it read: by the identity its welcome gave
ReviewName = Annotated[str, Field(max_length=MAX_ID_LENGTH)]
# A run of the review, as a page names the one it read
RunName = Annotated[str, Field(max_length=MAX_ID_LENGTH)]
# The number of a push in one run's telling. The first push is numbered one,
# so a page that has heard none of them says zero.
PushNumber = Annotated[int, Field(ge=0)]


class Resume(WireModel):
    """Where a page coming back had got to: which review, which run of it, and the number of the last push it covers.

    Named in the socket's address — `?identity=…&instance=…&after=…` —
    rather than said on the socket: the welcome, and whatever the page
    missed after it, are told before the page could say anything. A page
    that has not read its review yet names none of it: it was served by the
    review that answers, and its socket only holds that review on screen
    while it reads it. One naming another review is a page left open on a
    review that ran on the port before: it is welcomed, so it learns whose
    review answers now, and let go without counting as this review's page.
    """

    model_config = ConfigDict(frozen=True)

    identity: ReviewName
    instance: RunName
    after: PushNumber

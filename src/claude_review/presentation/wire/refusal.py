"""What a refused request is answered with: why, in words or field by field.

The review words its own refusals; FastAPI says, field by field, what a
request had wrong before any route saw it. Both answer under `detail`, so a
caller reads one shape whichever refused, and the API describes it once.
"""

from enum import StrEnum, auto

from claude_review.presentation.wire.base import WireModel


class RequestPart(StrEnum):
    """The part of a request a refused field came in: what FastAPI heads the field's place with.

    BODY — its JSON body, where the review too names what it finds wrong in one.
    QUERY — its query string.
    PATH — its path.
    """

    BODY = auto()
    QUERY = auto()
    PATH = auto()


# Every part of a request, to tell the head of a field's place from a name of the field's own
REQUEST_PARTS = frozenset(RequestPart)


class FieldRefusal(WireModel):
    """One field a request had wrong, as pydantic and FastAPI both describe it."""

    loc: tuple[str | int, ...]
    msg: str

    def without_request_part(self) -> FieldRefusal:
        """The refusal with its field named as whoever sent it knows it.

        The part of the request the field came in says nothing to whoever
        typed a command; what leads to the field from there is what they
        wrote. Only that head is left out: a field may itself be called
        `path`.
        """
        named = self.loc[1:] if self.loc and self.loc[0] in REQUEST_PARTS else self.loc
        return FieldRefusal(loc=named, msg=self.msg)


class Refusal(WireModel):
    """Why a request was refused: said in words, or field by field."""

    detail: str | list[FieldRefusal]

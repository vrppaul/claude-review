"""What a refused request is answered with: why, in words or field by field.

The review words its own refusals; FastAPI says, field by field, what a
request had wrong before any route saw it. Both answer under `detail`, so a
caller reads one shape whichever refused, and the API describes it once.
"""

from claude_review.presentation.wire.base import WireModel

# The part of a request a field of its JSON body is named under: FastAPI's
# word for it, and the review's for what it finds wrong in a body itself
REQUEST_BODY = "body"


class FieldRefusal(WireModel):
    """One field a request had wrong, as pydantic and FastAPI both describe it."""

    loc: tuple[str | int, ...]
    msg: str


class Refusal(WireModel):
    """Why a request was refused: said in words, or field by field."""

    detail: str | list[FieldRefusal]

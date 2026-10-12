"""A refusal as the answer its caller is sent: JSON, written by the model itself.

Every refusal leaves by this one door, whoever makes it — the review's
handlers, or the guard that stands before every route — so a model is
written to the wire as JSON and never taken apart into a mapping on the
way.
"""

from http import HTTPStatus

from starlette.responses import Response

from claude_review.presentation.wire.refusal import Refusal

# What a refusal is written in
JSON_MEDIA_TYPE = "application/json"


def answered(refusal: Refusal, status: HTTPStatus) -> Response:
    """The answer that says a refusal, with the status it is refused with."""
    return Response(content=refusal.model_dump_json(), status_code=status, media_type=JSON_MEDIA_TYPE)

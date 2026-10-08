"""The review's API as one OpenAPI document, for the browser's types to be generated from.

The routes describe themselves. The session socket does not — OpenAPI has no
words for a websocket — so this document alone describes it as a route of
its own: what the browser says on it is the body, what the server pushes is
the answer. Described that way, its schemas are named by the same hand as
everything else, and the browser reads one source for both.

Run as a module, it prints the document: `python -m claude_review.presentation.api_schema`.
"""

import json
import sys

from fastapi import APIRouter, FastAPI

from claude_review.presentation.app import API_TITLE
from claude_review.presentation.routes import router
from claude_review.presentation.schemas import ServerPush, SessionHello

# Where the socket is served, and where this document describes it
SESSION_ROUTE = "/api/session"

socket_description = APIRouter()


@socket_description.post(
    SESSION_ROUTE,
    summary="The session socket",
    description="A websocket, described here and never served as a route.",
    response_model=ServerPush,
)
async def session_socket(hello: SessionHello) -> None:
    """What the browser says on the socket, and what the server pushes down it."""


def api_schema() -> dict:
    """The OpenAPI document: every route, and what travels on the socket."""
    app = FastAPI(title=API_TITLE)
    app.include_router(router)
    app.include_router(socket_description)
    return app.openapi()


if __name__ == "__main__":
    json.dump(api_schema(), sys.stdout, indent=2)

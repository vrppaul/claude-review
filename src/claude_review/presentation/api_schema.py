"""What crosses the wire, written down for the browser's types to be generated from.

Two documents, because two things cross it. The routes describe themselves
as OpenAPI. The session socket is not HTTP, and OpenAPI has no words for it:
what the browser says on it — and names in its address as it opens it — is
read by the server, and what the server pushes is written by it, so each is
described in its own direction, in a document of their own that holds
nothing but their schemas.

Run as a module, it prints one: `python -m claude_review.presentation.api_schema http`
or `... api_schema socket`.
"""

import json
import sys
from collections.abc import Callable
from typing import NamedTuple

import click
from fastapi import FastAPI
from pydantic import JsonValue, TypeAdapter
from pydantic.json_schema import JsonSchemaMode

from claude_review.presentation.app import API_TITLE
from claude_review.presentation.routes.api import include_api
from claude_review.presentation.wire.session import Resume, SessionMessage
from claude_review.presentation.wire.threads import SessionHello

# The OpenAPI version both documents are written in
OPENAPI_VERSION = "3.1.0"
SOCKET_TITLE = f"{API_TITLE} session socket"
# The socket document has no version of its own; it changes with the server
SOCKET_VERSION = "1"
# Where OpenAPI keeps named schemas, as a reference into the document spells it
SCHEMA_REFERENCE = "#/components/schemas/{model}"


class SocketSchema(NamedTuple):
    """One thing said on the socket, or in its address, as pydantic is asked to describe it.

    A named tuple because `TypeAdapter.json_schemas` takes each as a
    `(key, mode, adapter)` triple: the fields keep that order.
    """

    # Its name in the document, which is the name of its type
    name: str
    # Read by the server, or written by it: a field with a default may be
    # left out of the one, and is always there in the other
    direction: JsonSchemaMode
    adapter: TypeAdapter[SessionHello] | TypeAdapter[Resume] | TypeAdapter[SessionMessage]


SOCKET_SCHEMAS = (
    SocketSchema("SessionHello", "validation", TypeAdapter(SessionHello)),
    SocketSchema("Resume", "validation", TypeAdapter(Resume)),
    SocketSchema("SessionMessage", "serialization", TypeAdapter(SessionMessage)),
)


class MissingSocketSchemaError(Exception):
    """Raised when something said on the socket is not described under its own name."""


def http_document() -> dict[str, JsonValue]:
    """Every route the review serves, as OpenAPI: mounted as a review's app mounts them, with no review behind them."""
    app = FastAPI(title=API_TITLE)
    include_api(app)
    return app.openapi()


def socket_document() -> dict[str, JsonValue]:
    """What travels on the session socket, as the schemas of an OpenAPI document with no paths."""
    _, definitions = TypeAdapter.json_schemas(SOCKET_SCHEMAS, ref_template=SCHEMA_REFERENCE)
    schemas = definitions["$defs"]
    missing = [described.name for described in SOCKET_SCHEMAS if described.name not in schemas]
    if missing:
        msg = f"not described under their own names: {', '.join(missing)}"
        raise MissingSocketSchemaError(msg)
    return {
        "openapi": OPENAPI_VERSION,
        "info": {"title": SOCKET_TITLE, "version": SOCKET_VERSION},
        "paths": {},
        "components": {"schemas": schemas},
    }


# Each document by the name it is asked for
DOCUMENTS: dict[str, Callable[[], dict[str, JsonValue]]] = {"http": http_document, "socket": socket_document}


@click.command()
@click.argument("document", type=click.Choice(list(DOCUMENTS)))
def print_document(*, document: str) -> None:
    """Print one of the documents the browser's types are generated from."""
    json.dump(DOCUMENTS[document](), sys.stdout, indent=2)


if __name__ == "__main__":
    print_document()

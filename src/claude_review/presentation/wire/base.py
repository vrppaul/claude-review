"""What every model on the wire shares, and the bounds every request is held to.

The review's own models say what the review is; these say what crosses to
its page and its agent. They are kept apart so the one can change without
the other, and so the rules of the wire — every field written out, every
id and text bounded — live on the wire alone.
"""

from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, Strict

from claude_review.services.image_service import MAX_IMAGES_PER_MESSAGE


class WireModel(BaseModel):
    """A model that crosses the wire: written out, it carries every field.

    A field with a default may be left out by whoever sends one, but the
    review always writes it, so the schema of what it writes says so — and
    the browser's types, generated from that schema, do not call such a
    field maybe missing. It is built from the review's own model of the same
    shape, field by field.
    """

    model_config = ConfigDict(json_schema_serialization_defaults_required=True, from_attributes=True)

    @classmethod
    def of(cls, source: BaseModel) -> Self:
        """The wire's form of one of the review's own models, read field by field."""
        return cls.model_validate(source, from_attributes=True)


# The most one thing said may hold: a comment, a turn, a panel message
MAX_TEXT_LENGTH = 50_000

# The longest id a request may name: a thread, a question, a message, an
# image, a base
MAX_ID_LENGTH = 200

# What an id may hold. A thread is read back at a path of its own —
# `/api/catch-up/threads/{id}` — where a slash would name another route, so
# an id is letters, digits, dots, dashes and underscores, and nothing else.
SAFE_ID = r"^[A-Za-z0-9._-]+$"

# An id as a request names it: a thread, a turn, a question, a message, an image
WireId = Annotated[str, Field(min_length=1, max_length=MAX_ID_LENGTH, pattern=SAFE_ID)]

# A yes or a no as JSON says it: true or false, never 0, 1 or "yes", which
# pydantic would otherwise read as one
WireBool = Annotated[bool, Strict()]


def _says_something(text: str) -> str:
    """Refuse text that is only blanks: on screen it would be a turn with nothing in it."""
    if not text.strip():
        msg = "says nothing"
        raise ValueError(msg)
    return text


# What the agent says — an answer, a panel message, a thread it raises:
# words, since it has no screenshots to send
AgentText = Annotated[str, Field(min_length=1, max_length=MAX_TEXT_LENGTH), AfterValidator(_says_something)]

# Ids handed out by POST /api/images, as many as one thing said may carry
ImageIds = Annotated[list[WireId], Field(max_length=MAX_IMAGES_PER_MESSAGE)]

# How long an agent's poll for events waits when it does not say: long enough
# that a loop of polls costs nothing, short enough to stay under the timeouts
# of whatever runs the command
DEFAULT_WAIT_SECONDS = 25.0
# The longest one poll may wait, so a caller that asks for more is told so
# rather than left holding a connection for good
MAX_WAIT_SECONDS = 600.0

# The most threads one review hands over at once. A review with more is
# not a review any more, and the requests that carry them stay bounded.
MAX_THREADS = 500

# The most files one thing the agent says may hang off it, as chips
MAX_FILES_NAMED = 20

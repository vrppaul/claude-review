"""What every schema of the API shares, and the bounds every request is held to.

The domain's models say what the review is; the API's schemas say what its
page and its agent send and are sent. They are kept apart so the one can
change without the other, and so the API's rules — every field written out,
every id and text a request carries bounded — live in the schemas alone. All
but what an id may hold: the review holds a story's chapters to that as well,
so the rule is the domain's, and the schemas bound their ids by it.
"""

from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    PlainValidator,
    WithJsonSchema,
)

from claude_review.domain.models import MAX_ID_LENGTH, SAFE_ID, LineSpan, says_nothing
from claude_review.services.image_service import MAX_IMAGES_PER_MESSAGE
from claude_review.services.place_words import LINES_EXAMPLE, LINES_WRITTEN, line_span, lines_named

# What JSON is called in a request or an answer, for whoever writes it by hand: the agent's client says it of
# what it sends, and a refusal of itself. The answers FastAPI writes say it themselves
JSON_MEDIA_TYPE = "application/json"


class Schema(BaseModel):
    """A schema of the API: written out, it carries every field.

    A field with a default may be left out by whoever sends one, but the
    review always writes it, so the schema of what it writes says so — and
    the browser's types, generated from that schema, do not call such a
    field maybe missing. One the review sends is made from the domain's model
    of the same shape, field by field.
    """

    model_config = ConfigDict(json_schema_serialization_defaults_required=True, from_attributes=True)

    @classmethod
    def from_domain(cls, source: BaseModel) -> Self:
        """The schema of one of the domain's models, read field by field."""
        return cls.model_validate(source, from_attributes=True)

    @classmethod
    def from_domain_or_none(cls, source: BaseModel | None) -> Self | None:
        """The schema of one of the domain's models where there may be none: none in the answer too."""
        return cls.from_domain(source) if source is not None else None


# The most one thing said may hold: a comment, a turn, a panel message
MAX_TEXT_LENGTH = 50_000

# An id as a request names it, in its body or in a route's path: a thread, a
# turn, a question, a message, an image. Held to the review's one rule for an
# id (`SAFE_ID`), which a story's chapter is held to as well: a thread is read
# back at a path of its own, `/api/catch-up/threads/{id}`, where a slash would
# name another route
SafeId = Annotated[str, Field(min_length=1, max_length=MAX_ID_LENGTH, pattern=SAFE_ID)]


def _says_something(text: str) -> str:
    """Refuse text that is only blanks: on screen it would be a turn with nothing in it."""
    if says_nothing(text):
        msg = "says nothing"
        raise ValueError(msg)
    return text


# What the agent says — an answer, a panel message, a thread it raises:
# words, since it has no screenshots to send
AgentText = Annotated[str, Field(min_length=1, max_length=MAX_TEXT_LENGTH), AfterValidator(_says_something)]

# How the API describes a step's lines: text, as `LINES_WRITTEN` has it
LINES_SCHEMA = {"type": "string", "pattern": LINES_WRITTEN.pattern}
NOT_TEXT = f"wants lines as text, like {LINES_EXAMPLE}"


def _lines_read(written: object) -> LineSpan:
    """A step's lines as the agent wrote them, read; lines the review holds already are taken as they are.

    Raises:
        ValueError: if they are neither, or text that names no lines: what
            pydantic reads as a field refused, where any other error would
            be a fault of this side.
    """
    match written:
        case LineSpan():
            return written
        case str():
            return lines_named(written)
        case _:
            raise ValueError(NOT_TEXT)


def _lines_written(lines: LineSpan) -> str:
    """A step's lines as the agent writes them: in a document sent on as read, and in what it is told of a step."""
    return line_span(lines.first, lines.last)


# A step's lines as the agent writes and reads them: "42" or "104-129", held as the lines they name
LinesWritten = Annotated[
    LineSpan,
    PlainValidator(_lines_read),
    PlainSerializer(_lines_written, return_type=str),
    WithJsonSchema(LINES_SCHEMA),
]

# Ids handed out by POST /api/images, as many as one thing said may carry
ImageIds = Annotated[list[SafeId], Field(max_length=MAX_IMAGES_PER_MESSAGE)]

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

"""What the agent's commands take, each read against the rule the review holds it to.

Read here, as the command is parsed, so a value the review would refuse is
the typist's to fix, said naming the option or argument it was typed in,
and no request the review would refuse is ever built.
"""

from typing import Self, override

import click
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from claude_review.cli.review_client import REASON_SEPARATOR
from claude_review.domain.models import FilePath, StepText
from claude_review.presentation.wire.agent import ProgressText, StatusText
from claude_review.presentation.wire.base import AgentText, WireId

# What joins the first line of a range to its last
RANGE_SEPARATOR = "-"


class CheckedParameter(click.ParamType):
    """A value read against the rule the review holds it to."""

    def __init__(self, name: str, rule: TypeAdapter[str]) -> None:
        self.name = name
        self._rule = rule

    @override
    def convert(self, value: object, param: click.Parameter | None, ctx: click.Context | None) -> str:
        try:
            return self._rule.validate_python(value)
        except ValidationError as invalid:
            reasons = REASON_SEPARATOR.join(detail["msg"] for detail in invalid.errors())
            self.fail(f"the review would refuse {value!r}: {reasons}", param, ctx)


# An id the review gave out: a thread, a question, a message
ID = CheckedParameter("id", TypeAdapter[str](WireId))
# A file as the diff names it
FILE = CheckedParameter("path", TypeAdapter[str](FilePath))
# What the agent says: words that say something
SAID = CheckedParameter("text", TypeAdapter[str](AgentText))
# What the agent is doing, and what that has branched into
WORK = CheckedParameter("text", TypeAdapter[str](ProgressText))
STEP = CheckedParameter("text", TypeAdapter[str](StepText))
# What the agent says about itself
STATUS = CheckedParameter("text", TypeAdapter[str](StatusText))


class LineSpan(BaseModel):
    """The lines of a file a thread hangs on, first to last."""

    model_config = ConfigDict(frozen=True)

    first: int = Field(ge=1)
    last: int = Field(ge=1)

    @model_validator(mode="after")
    def runs_forwards(self) -> Self:
        if self.last < self.first:
            msg = "the range runs backwards"
            raise ValueError(msg)
        return self


class LineSpanParameter(click.ParamType):
    """Reads "42" or "42-47" as the lines a thread hangs on."""

    name = "lines"

    @override
    def convert(self, value: object, param: click.Parameter | None, ctx: click.Context | None) -> LineSpan:
        if isinstance(value, LineSpan):
            return value
        first, separator, last = str(value).partition(RANGE_SEPARATOR)
        try:
            return LineSpan(first=int(first), last=int(last) if separator else int(first))
        # Both a number that is no number and a span that breaks its own rules say no this way
        except ValueError:
            self.fail(f'wants a line or a range from line 1 on, like "42" or "42-47", not "{value}"', param, ctx)


LINE_SPAN = LineSpanParameter()

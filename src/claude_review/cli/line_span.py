"""The lines a thread raised from the command line hangs on: `--lines 42` or `--lines 42-47`."""

from typing import Self

import click
from pydantic import BaseModel, ConfigDict, Field, model_validator

# What joins the first line of a range to its last
RANGE_SEPARATOR = "-"


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

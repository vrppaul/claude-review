"""What the agent's commands take, each read against the rule the review holds it to.

Read here, as the command is parsed, so a value the review would refuse is
the typist's to fix, said naming the option or argument it was typed in,
and no request the review would refuse is ever built.
"""

from typing import Self, override

import click
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from claude_review.cli.review_client import REASON_SEPARATOR
from claude_review.domain.models import FIRST_LINE, MAX_QUOTE_LINES, FilePath, StepText, runs_backwards
from claude_review.presentation.wire.agent import MAX_PROGRESS_STEPS, ProgressText, StatusText
from claude_review.presentation.wire.base import MAX_FILES_NAMED, AgentText, WireId

# What joins the first line of a range to its last
RANGE_SEPARATOR = "-"
# What stands for stdin where text is wanted, as it does for `git commit -F -`,
# and stdin as click names it among the process's streams
FROM_STDIN = "-"
STDIN = "stdin"
# What text piped in is written in, and the line break a heredoc or an echo
# ends it with: the shell's, not part of what was said
STDIN_ENCODING = "utf-8"
TRAILING_LINE_BREAK = "\n"


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
            self.fail(f"the review would refuse {value!r}: {_reasons(invalid)}", param, ctx)


class TextParameter(CheckedParameter):
    """Text read against the rule the review holds it to, from stdin when it is given as "-".

    Inside double quotes the shell runs whatever sits in backticks and empties
    every `$name`, and an answer in Markdown is full of both. Piped in from a
    quoted heredoc, it arrives as it was written.
    """

    @override
    def convert(self, value: object, param: click.Parameter | None, ctx: click.Context | None) -> str:
        if value != FROM_STDIN:
            return super().convert(value, param, ctx)
        try:
            piped = click.get_binary_stream(STDIN).read().decode(STDIN_ENCODING)
        except UnicodeDecodeError:
            self.fail(f"what stdin handed over is not {STDIN_ENCODING.upper()} text", param, ctx)
        return super().convert(piped.removesuffix(TRAILING_LINE_BREAK), param, ctx)


# An id the review gave out: a thread, a question, a message
ID = CheckedParameter("id", TypeAdapter[str](WireId))
# A file as the diff names it
FILE = CheckedParameter("path", TypeAdapter[str](FilePath))
# What the agent says: words that say something
SAID = TextParameter("text", TypeAdapter[str](AgentText))
# What the agent is doing, and what that has branched into
WORK = TextParameter("text", TypeAdapter[str](ProgressText))
STEP = CheckedParameter("text", TypeAdapter[str](StepText))
# What the agent says about itself
STATUS = CheckedParameter("text", TypeAdapter[str](StatusText))


class EachOnce:
    """What a repeatable option was typed with, read as the review reads its list: each once, and no more than it takes.

    A value typed twice was meant once, and goes once, where it was first
    typed: the review refuses a list that names one twice. More values than
    the review takes are the typist's to fix, said naming the option.
    """

    def __init__(self, bound: int) -> None:
        self._bound = bound

    def __call__(self, context: click.Context, parameter: click.Parameter, values: tuple[str, ...]) -> tuple[str, ...]:
        distinct = tuple(dict.fromkeys(values))
        if len(distinct) > self._bound:
            msg = f"the review takes at most {self._bound}, not {len(distinct)}"
            raise click.BadParameter(msg, ctx=context, param=parameter)
        return distinct


# The files hung off what the agent says, or off what it is doing
NAMED_FILES = EachOnce(MAX_FILES_NAMED)
# The branches of the work, done or under way
BRANCHES = EachOnce(MAX_PROGRESS_STEPS)


class LineSpan(BaseModel):
    """The lines of a file a thread hangs on, first to last, no more than a thread may quote."""

    model_config = ConfigDict(frozen=True)

    first: int = Field(ge=FIRST_LINE)
    last: int = Field(ge=FIRST_LINE)

    @model_validator(mode="after")
    def runs_forwards(self) -> Self:
        if runs_backwards(self.first, self.last):
            msg = "the range runs backwards"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def quotable(self) -> Self:
        line_count = self.last - self.first + 1
        if line_count > MAX_QUOTE_LINES:
            msg = f"a thread may hang on at most {MAX_QUOTE_LINES} lines, not {line_count}"
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
            first_line = int(first)
            last_line = int(last) if separator else first_line
        except ValueError:
            self.fail(
                f'wants a line or a range from line {FIRST_LINE} on, like "42" or "42-47", not "{value}"', param, ctx
            )
        try:
            return LineSpan(first=first_line, last=last_line)
        except ValidationError as invalid:
            self.fail(f'the review would refuse "{value}": {_reasons(invalid)}', param, ctx)


LINE_SPAN = LineSpanParameter()


def _reasons(invalid: ValidationError) -> str:
    """Why a value was refused, in the words of each rule it broke, on one line."""
    return REASON_SEPARATOR.join(detail["msg"] for detail in invalid.errors())

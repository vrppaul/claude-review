"""Run a command to its end and say how it went: the one way a script here runs one.

`look.py` drives the review through its command line and `break_lines.py`
the page's tools through pnpm, so each runs commands and waits for them. A
command is started through asyncio, as the review itself starts git: the
script that runs it stays able to wait with a limit and to stop what it
started when it is itself cancelled. bandit, which reads the scripts,
refuses the `subprocess` module and has no rule for this form.
"""

import asyncio
from asyncio.subprocess import PIPE, STDOUT
from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict

# What a command that did what it was asked exits with
SUCCEEDED = 0
# What is said of one that did not
FAILED = "`{command}` failed: {said}"


class CommandFailedError(Exception):
    """A command a script cannot go on without failed: what the error says is the command and what it printed."""


class Ran(BaseModel):
    """A command run to its end: what it was, what it exited with, and all it printed."""

    model_config = ConfigDict(frozen=True)

    command: tuple[str, ...]
    exit_code: int
    said: str

    def must_have_succeeded(self) -> None:
        """Hold the command to having done what it was asked.

        Raises:
            CommandFailedError: if it exited with anything but success.
        """
        if self.exit_code != SUCCEEDED:
            failure = FAILED.format(command=" ".join(self.command), said=self.said)
            raise CommandFailedError(failure)


async def run(command: Sequence[str], environment: Mapping[str, str]) -> Ran:
    """Run a command to its end, in the environment given, and say what it exited with and printed."""
    process = await asyncio.create_subprocess_exec(*command, env=environment, stdout=PIPE, stderr=STDOUT)
    printed, _ = await process.communicate()
    return Ran(command=tuple(command), exit_code=await process.wait(), said=printed.decode().strip())

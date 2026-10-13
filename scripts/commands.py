"""Every process a script starts, and how a script's work is run so that none outlives it.

`look.py` drives the review through its command line and `break_lines.py`
the page's tools through pnpm: each runs commands to their end, and the look
starts one that stays, the review's server. They are all started here, so
that two things hold of every script. A wait has a limit: a command still
running when its limit runs out is stopped, and said to have failed. And
nothing a script starts outlives it: a script's work is one coroutine
handed to `complete`, which cancels it when the script is told from outside
to stop, by SIGTERM or at Ctrl-C, and a command or a server running at that
moment is stopped on the way out.

A process is started as the head of a group of its own and stopped as that
group, by its pid: pnpm starts vitest, and a stop that reached pnpm alone
would leave vitest running over a directory already removed.

Processes are started through asyncio, as the review itself starts git:
waiting with a limit and stopping on the way out of cancelled work are what
that form is for. bandit, which reads the scripts, refuses the `subprocess`
module and has no rule for this form; `check_code_rules.py` holds every
other script to starting its processes here.
"""

import asyncio
import contextlib
import os
import signal
from asyncio.subprocess import DEVNULL, PIPE, STDOUT, Process
from collections.abc import AsyncGenerator, Coroutine, Mapping, Sequence

from pydantic import BaseModel, ConfigDict

# What a command that did what it was asked exits with
SUCCEEDED = 0
# What a script exits with when it is stopped from outside, as a shell says of a program stopped at Ctrl-C
STOPPED_FROM_OUTSIDE = 130
# How long a process has to end once told to, before it is stopped outright
STOPPED_WITHIN_SECONDS = 10

# What is said of a command that failed, of one that ran out of time, and of one started with nowhere to say anything
FAILED = "`{command}` failed: {said}"
OUT_OF_TIME = "`{command}` had not ended after {seconds} seconds, and was stopped"
NO_PIPE = "`{command}` was started with no pipe for what it says on stderr"


class CommandFailedError(Exception):
    """A command a script cannot go on without failed: what the error says is the command and what it printed."""


class StoppedError(Exception):
    """The script was told from outside to stop, and what it had started is stopped."""


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


class Running:
    """A command that stays until the script is done with it: what it says on stderr, and when it has ended."""

    def __init__(self, process: Process, errors: asyncio.StreamReader) -> None:
        self._process = process
        self._errors = errors

    async def line_said(self) -> str:
        """The next line it says on stderr; nothing once it has no more to say."""
        return (await self._errors.readline()).decode()

    async def ended(self) -> None:
        """Wait until it ends of itself."""
        await self._process.wait()


def _signal(process: Process, sent: signal.Signals) -> None:
    """Send a signal to a process and to whatever it started: one group, named by the process's pid."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, sent)


async def _stop(process: Process) -> None:
    """Stop a process and what it started, and wait until it is gone: told to first, then stopped outright."""
    _signal(process, signal.SIGTERM)
    try:
        await asyncio.wait_for(process.wait(), timeout=STOPPED_WITHIN_SECONDS)
    except TimeoutError:
        _signal(process, signal.SIGKILL)
        await process.wait()


async def run(command: Sequence[str], environment: Mapping[str, str], within_seconds: float) -> Ran:
    """Run a command to its end, in the environment given, and say what it exited with and printed.

    Raises:
        CommandFailedError: if it has not ended within the limit; it is stopped first.
    """
    process = await asyncio.create_subprocess_exec(
        *command, env=environment, stdout=PIPE, stderr=STDOUT, start_new_session=True
    )
    try:
        printed, _ = await asyncio.wait_for(process.communicate(), timeout=within_seconds)
    except TimeoutError as error:
        await _stop(process)
        failure = OUT_OF_TIME.format(command=" ".join(command), seconds=within_seconds)
        raise CommandFailedError(failure) from error
    except BaseException:
        # Cancelled while the command was running: it goes with the script's work
        await _stop(process)
        raise
    return Ran(command=tuple(command), exit_code=await process.wait(), said=printed.decode().strip())


@contextlib.asynccontextmanager
async def running(command: Sequence[str], environment: Mapping[str, str]) -> AsyncGenerator[Running]:
    """Start a command that stays, and stop it by its pid as the block ends, however the block ends."""
    process = await asyncio.create_subprocess_exec(
        *command, env=environment, stdout=DEVNULL, stderr=PIPE, start_new_session=True
    )
    try:
        yield Running(process, _errors_of(process, command))
    finally:
        await _stop(process)


def _errors_of(process: Process, command: Sequence[str]) -> asyncio.StreamReader:
    """Where a process started with a pipe for its errors says them."""
    if process.stderr is None:
        failure = NO_PIPE.format(command=" ".join(command))
        raise CommandFailedError(failure)
    return process.stderr


async def _until_told_to_stop[ResultT](work: Coroutine[None, None, ResultT]) -> ResultT:
    """Do the work, cancelling it where it stands when SIGTERM comes, as asyncio cancels it at Ctrl-C."""
    working = asyncio.create_task(work)
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, working.cancel)
    return await working


def complete[ResultT](work: Coroutine[None, None, ResultT]) -> ResultT:
    """Run a script's work to its end, and give what it gives.

    Raises:
        StoppedError: if the script is told from outside to stop before the work is done.
    """
    try:
        return asyncio.run(_until_told_to_stop(work))
    except (KeyboardInterrupt, asyncio.CancelledError) as stopped:
        raise StoppedError from stopped

"""`scripts/commands.py`: what a script starts is stopped whole, and a wait has a limit.

Held through a script of a few lines the test writes and runs as a script is
run, since what is asked is of processes. The script starts a command, the
command starts a child, and the child is what is asked after: stopped as a
group, it is gone with the command, and stopped alone, the command would
leave it running. The child says in a pipe that it runs, and holds that
pipe open for as long as it lives, so the pipe coming to its end is that
process ended: nothing is looked for over and over. What it says there is
its pid and the command's, by which a test whose script did not stop them
stops them itself.
"""

import contextlib
import os
import select
import signal
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from textwrap import dedent

import pytest
from pydantic import BaseModel, ConfigDict

SCRIPTS = Path(__file__).parents[2] / "scripts"
# Where Python looks for a module a script imports by its bare name, as a script in `scripts/` finds `commands`
MODULES_VARIABLE = "PYTHONPATH"

# What a script exits with: its work done, a command failed, and stopped from outside
DONE = 0
FAILED = 1
STOPPED_FROM_OUTSIDE = 130
# How long a script written here may take, a child has to say its pid, and to be gone once stopped
SCRIPT_SECONDS = 30
SAID_WITHIN_SECONDS = 10
GONE_WITHIN_SECONDS = 5
# The most two pids take to write, in bytes
PIDS_LENGTH = 64
# A limit a command that stays outlasts, in seconds
A_SHORT_LIMIT = 1
# What a script waiting to be told to go on reads
GO_ON = "\n"

# The child: it says its pid and the command's in the pipe it is given, and stays, the pipe open
A_CHILD_THAT_STAYS = dedent('''\
    """Say this process's pid and its parent's where whoever started all this reads them, and stay, holding that open."""

    import os
    import sys
    import time

    said = open(sys.argv[1], "w")
    said.write(f"{os.getpid()} {os.getppid()}")
    said.flush()
    time.sleep(60)
    ''')

# The command a script runs: it starts the child, handing on what it was given, and stays too
A_COMMAND_WITH_A_CHILD = dedent('''\
    """Start a child that stays, and stay."""

    import subprocess
    import sys
    import time

    subprocess.Popen([sys.executable, *sys.argv[1:]])
    time.sleep(60)
    ''')

# A script that starts a command which stays, and leaves the block it runs in once told to go on
LEAVES_THE_BLOCK = dedent('''\
    """Start the command given, wait to be told to go on, and leave the block the command runs in."""

    import asyncio
    import os
    import sys

    from commands import complete, running


    async def work() -> None:
        async with running(sys.argv[1:], dict(os.environ)):
            await asyncio.to_thread(sys.stdin.readline)


    complete(work())
    ''')

# A script that runs a command to its end, and exits as a script stopped from outside does
RUNS_TO_THE_END = dedent('''\
    """Run the command given to its end, with all the time it could want."""

    import os
    import sys

    from commands import STOPPED_FROM_OUTSIDE, StoppedError, complete, run

    try:
        complete(run(sys.argv[1:], dict(os.environ), within_seconds=600))
    except StoppedError:
        sys.exit(STOPPED_FROM_OUTSIDE)
    ''')

# A script that runs a command with the limit given, and says why the command failed
RUNS_WITH_A_LIMIT = dedent('''\
    """Run the command given after the limit, within that limit, and say what is said of it if it fails."""

    import os
    import sys

    from commands import CommandFailedError, complete, run

    try:
        complete(run(sys.argv[2:], dict(os.environ), within_seconds=int(sys.argv[1])))
    except CommandFailedError as failed:
        sys.exit(str(failed))
    ''')


class Staying(BaseModel):
    """A command that stays and starts a child that stays: how it is run, and where the child's pipe is read."""

    model_config = ConfigDict(frozen=True)

    command: tuple[str, ...]
    childs_pipe: int


def _written(directory: Path, name: str, text: str) -> Path:
    script = directory / name
    script.write_text(text)
    return script


@pytest.fixture
def staying(tmp_path: Path) -> Iterator[Staying]:
    """A command with a child, and the pipe the child says its pid in, open to be read before anything writes."""
    pipe = tmp_path / "pid"
    os.mkfifo(pipe)
    child = _written(tmp_path, "child.py", A_CHILD_THAT_STAYS)
    command = _written(tmp_path, "command.py", A_COMMAND_WITH_A_CHILD)
    read_at = os.open(pipe, os.O_RDONLY | os.O_NONBLOCK)
    yield Staying(command=(sys.executable, str(command), str(child), str(pipe)), childs_pipe=read_at)
    os.close(read_at)


def _started(script: Path, *arguments: str) -> subprocess.Popen[str]:
    """A script written here, started as a script is run, with `commands` where it looks for it."""
    return subprocess.Popen(
        [sys.executable, str(script), *arguments],
        env={**os.environ, MODULES_VARIABLE: str(SCRIPTS)},
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


@contextlib.contextmanager
def _child_running(staying: Staying) -> Iterator[None]:
    """Wait until the child says it runs. As the block ends, it and the command are stopped, where a script left them."""
    select.select([staying.childs_pipe], [], [], SAID_WITHIN_SECONDS)
    left_running = [int(pid) for pid in os.read(staying.childs_pipe, PIDS_LENGTH).split()]
    try:
        yield
    finally:
        for pid in left_running:
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, signal.SIGKILL)


def _has_ended(staying: Staying) -> bool:
    """Whether the child ends before long: its pipe, which it held open while it lived, comes to its end.

    The child writes in it once, so the pipe has something to say again only when it is over.
    """
    over, _, _ = select.select([staying.childs_pipe], [], [], GONE_WITHIN_SECONDS)
    return over == [staying.childs_pipe]


def test_a_command_is_stopped_with_the_child_it_started_as_the_block_it_runs_in_ends(
    tmp_path: Path, staying: Staying
) -> None:
    script = _started(_written(tmp_path, "leaves_the_block.py", LEAVES_THE_BLOCK), *staying.command)

    with _child_running(staying):
        script.communicate(GO_ON, timeout=SCRIPT_SECONDS)

        assert (script.returncode, _has_ended(staying)) == (DONE, True)


def test_a_command_being_run_is_stopped_with_its_child_when_the_script_is_stopped_from_outside(
    tmp_path: Path, staying: Staying
) -> None:
    script = _started(_written(tmp_path, "runs_to_the_end.py", RUNS_TO_THE_END), *staying.command)

    with _child_running(staying):
        script.send_signal(signal.SIGTERM)
        script.communicate(timeout=SCRIPT_SECONDS)

        assert (script.returncode, _has_ended(staying)) == (STOPPED_FROM_OUTSIDE, True)


def test_a_command_that_outlasts_its_limit_is_stopped_with_its_child_and_said_to_have_been(
    tmp_path: Path, staying: Staying
) -> None:
    limited = _written(tmp_path, "runs_with_a_limit.py", RUNS_WITH_A_LIMIT)
    script = _started(limited, str(A_SHORT_LIMIT), *staying.command)

    with _child_running(staying):
        _, said = script.communicate(timeout=SCRIPT_SECONDS)

        assert (script.returncode, said.strip(), _has_ended(staying)) == (
            FAILED,
            f"`{' '.join(staying.command)}` had not ended after {A_SHORT_LIMIT} seconds, and was stopped",
            True,
        )

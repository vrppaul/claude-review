"""The agent's side of a review a browser test drives: its commands, run as the agent runs them."""

import asyncio
import sys

from tests.helpers import RunningReview


async def as_the_agent(review: RunningReview, command: str, *arguments: str) -> str:
    """Run one of the agent's commands against the review, as the agent would, and return what it printed."""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "claude_review",
        command,
        "--port",
        str(review.port),
        *arguments,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    printed, said = await process.communicate()
    assert process.returncode == 0, said.decode()
    return printed.decode()

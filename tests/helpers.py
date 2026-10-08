"""Shared test utilities."""

import asyncio
import subprocess
from pathlib import Path

from httpx import AsyncClient


def git(repo: Path, *args: str) -> str:
    """Run a git command in the given repo and return stdout."""
    result = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return result.stdout


# How long a test waits for something it has set going before giving up on it
SETTLE_SECONDS = 5.0
# How often it looks while it waits
LOOK_EVERY_SECONDS = 0.01


async def until_an_agent_waits(client: AsyncClient, headers: dict[str, str] | None = None) -> None:
    """Return once a poll for events is waiting on the review.

    A poll says an agent is there before it starts to wait, with nothing in
    between to yield to: once the review reports an agent, the poll is
    waiting, and whatever the test does next wakes it rather than lands in
    the queue ahead of it.
    """
    deadline = asyncio.get_running_loop().time() + SETTLE_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        if (await client.get("/api/diff", headers=headers)).json()["answerer_attached"]:
            return
        await asyncio.sleep(LOOK_EVERY_SECONDS)
    msg = "no agent started waiting on the review"
    raise AssertionError(msg)

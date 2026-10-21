"""`scripts/look.py`: a smoke test, run as it is run.

A look only serves: it makes a long change, serves it with its story told,
says where, and stays until the review's page is closed. Read here as the
page reads it, by the review's routes and its socket: a test of a script
drives no browser.
"""

import asyncio
import contextlib
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import URL, AsyncClient
from pydantic import BaseModel, ConfigDict

from claude_review.presentation.schemas.content import DiffResponse
from claude_review.presentation.schemas.story import StoryResponse
from tests.helpers import DIFF_ROUTE, STORY_ROUTE
from tests.page_socket import PageSocket

REPOSITORY = Path(__file__).parents[2]
LOOK = REPOSITORY / "scripts" / "look.py"
# How long a look may take before it is cut: several times what one takes
LOOK_SECONDS = 60
# What a look exits with once its review has ended
ENDED = 0
# The files of the long change a look serves, and the chapters of the story it tells of it
FILES_OF_THE_CHANGE = 41
CHAPTERS_OF_THE_STORY = 6


class Look(BaseModel):
    """A look under way: where it says the review is, and its process."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    address: str
    process: asyncio.subprocess.Process


@pytest.fixture
async def look() -> AsyncIterator[Look]:
    """A look started as a person starts one, stopped after the test as a shell stops one."""
    process = await asyncio.create_subprocess_exec(
        sys.executable, str(LOOK), cwd=REPOSITORY, stdout=asyncio.subprocess.PIPE
    )
    said = await asyncio.wait_for(process.stdout.readline(), timeout=LOOK_SECONDS)
    _, address = said.decode().split()
    yield Look(address=address, process=process)
    with contextlib.suppress(ProcessLookupError):
        process.terminate()
    await process.wait()


async def test_a_look_serves_the_long_change_and_its_story_until_the_page_is_closed(look: Look) -> None:
    async with AsyncClient(base_url=look.address) as reader:
        diff = DiffResponse.model_validate_json((await reader.get(DIFF_ROUTE)).content)
        told = StoryResponse.model_validate_json((await reader.get(STORY_ROUTE)).content)
    page = await asyncio.to_thread(PageSocket, URL(look.address).port)

    page.close()

    assert (len(diff.files), len(told.held.story.chapters)) == (FILES_OF_THE_CHANGE, CHAPTERS_OF_THE_STORY)
    assert await asyncio.wait_for(look.process.wait(), timeout=LOOK_SECONDS) == ENDED

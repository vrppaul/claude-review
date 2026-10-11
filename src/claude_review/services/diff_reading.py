"""The review's diff, read from a staged tree."""

import asyncio

from claude_review.domain.interfaces import StagedTree
from claude_review.domain.models import DiffFile
from claude_review.services.unified_diff import parse_unified_diff


async def read_diff(staged: StagedTree, *, base: str, ignore_whitespace: bool) -> list[DiffFile]:
    """The diff of a staged tree against a base, as the review's files.

    Parsed off the event loop: a diff of thousands of files takes seconds to
    read, and the server has every page's socket and the agent's wait to
    keep answering meanwhile.
    """
    raw = await staged.diff(base, ignore_whitespace=ignore_whitespace)
    return await asyncio.to_thread(parse_unified_diff, raw)

"""The review's diff, read from a staged tree."""

import asyncio

from claude_review.domain.interfaces import StagedTree
from claude_review.domain.models import DiffFile, Unshown
from claude_review.services.unified_diff import parse_unified_diff


async def read_diff(staged: StagedTree, *, base: str, ignore_whitespace: bool) -> list[DiffFile]:
    """The diff of a staged tree against a base, as the review's files.

    Parsed off the event loop: a diff of thousands of files takes seconds to
    read, and the server has every page's socket and the agent's wait to
    keep answering meanwhile. A file git calls binary may only be too large
    for it to read; the staged tree is asked which.
    """
    raw = await staged.diff(base, ignore_whitespace=ignore_whitespace)
    files = await asyncio.to_thread(parse_unified_diff, raw)
    binary = [file for file in files if file.unshown is Unshown.BINARY]
    too_large = await staged.too_large_to_show(base, binary)
    return [file.unshown_for(Unshown.TOO_LARGE) if file.path in too_large else file for file in files]

"""The review's diff, read from a staged tree as it is taken, or from the tree a take was written down as.

Parsed off the event loop either way: a diff of thousands of files takes
seconds to read, and the server has every page's socket and the agent's
wait to keep answering meanwhile. A file git calls binary may only be too
large for it to read; whatever wrote the diff is asked which.
"""

import asyncio
from pathlib import Path

from claude_review.domain.interfaces import Repository, StagedTree
from claude_review.domain.models import DiffFile, Unshown
from claude_review.services.unified_diff import parse_unified_diff


async def read_diff(staged: StagedTree, *, base: str, ignore_whitespace: bool) -> list[DiffFile]:
    """The diff of a staged tree against a base, as the review's files."""
    raw = await staged.diff(base, ignore_whitespace=ignore_whitespace)
    files = await asyncio.to_thread(parse_unified_diff, raw)
    return _saying_which_are_too_large(files, await staged.too_large_to_show(base, _called_binary(files)))


async def read_diff_between(
    repository: Repository, root: Path, earlier: str, later: str, *, ignore_whitespace: bool
) -> list[DiffFile]:
    """The diff from a base or a tree written down to such a tree, as the review's files.

    Raises:
        GitError: if git cannot say it.
    """
    raw = await repository.diff_between(root, earlier, later, ignore_whitespace=ignore_whitespace)
    files = await asyncio.to_thread(parse_unified_diff, raw)
    too_large = await repository.too_large_between(root, earlier, later, _called_binary(files))
    return _saying_which_are_too_large(files, too_large)


def _called_binary(files: list[DiffFile]) -> list[DiffFile]:
    """The files git says are binary: those it could not read, and those it would not."""
    return [file for file in files if file.unshown is Unshown.BINARY]


def _saying_which_are_too_large(files: list[DiffFile], too_large: set[str]) -> list[DiffFile]:
    """The files, each of those too large to read saying so in place of what git said of it."""
    return [file.unshown_for(Unshown.TOO_LARGE) if file.path in too_large else file for file in files]

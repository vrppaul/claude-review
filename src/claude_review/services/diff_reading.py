"""The review's diff, read from a staged tree."""

from claude_review.domain.interfaces import StagedTree
from claude_review.domain.models import DiffFile
from claude_review.services.unified_diff import parse_unified_diff


async def read_diff(staged: StagedTree, *, base: str, ignore_whitespace: bool) -> list[DiffFile]:
    """The diff of a staged tree against a base, as the review's files."""
    return parse_unified_diff(await staged.diff(base, ignore_whitespace=ignore_whitespace))

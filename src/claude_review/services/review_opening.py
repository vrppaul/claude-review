"""What a review opens on: its content, read once, and what names it.

Each kind of review reads its content its own way, and names itself its own
way; everything after that — the port, the server, the way out — is the
same for all three. Paths are resolved here, before anything else: what
makes two openings the same review is where the files are, not how they
were named.
"""

import asyncio
from pathlib import Path

import structlog
from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import DiffFile, ReviewMode
from claude_review.domain.protocols import GitRepositoryProtocol
from claude_review.services.diff_reading import read_diff
from claude_review.services.text_files import read_text_files
from claude_review.services.transcript import read_transcript

log = structlog.get_logger()

# How many files a files review names in its title before it counts the rest
FILES_NAMED_IN_TITLE = 3


class ReviewOpening(BaseModel):
    """What a review opens on, read and named."""

    model_config = ConfigDict(frozen=True)

    mode: ReviewMode
    diff_files: list[DiffFile]
    # What the header says is under review. It is also what an unsent draft
    # is kept under, so it must not change between two openings of the same thing.
    title: str
    # What makes it the same review when it is opened again: that lands it on
    # the same port, and so on the draft its reader left in it
    identity: str
    # The repository a diff review reads from, and the base it compares
    # against; a review of files or of a conversation has neither
    root: Path | None
    base: str | None


async def open_diff(location: Path, base: str | None, git_repository: GitRepositoryProtocol) -> ReviewOpening:
    """The changes in the repository `location` is in, against `base`, or uncommitted ones without it.

    Git reports paths relative to the repository root rather than to the
    directory it was run in, so the review is told the root, not `location`:
    anything that reads those paths later — expanding a hunk's context — has
    to start there.
    """
    resolved_location = await asyncio.to_thread(location.resolve)
    log.info("loading_diff", path=str(resolved_location), base=base)
    async with git_repository.staged(resolved_location) as staged:
        diff_files = await read_diff(staged, base=base, ignore_whitespace=False)
    root = await git_repository.top_level(resolved_location) or resolved_location
    return ReviewOpening(
        mode=ReviewMode.DIFF,
        diff_files=diff_files,
        title=_diff_title(root, base),
        identity=f"{root}\n{base or ''}",
        root=root,
        base=base,
    )


async def open_files(paths: list[Path], *, named_from: Path) -> ReviewOpening:
    """Text files — plans, docs, configs, source code — each read whole, and named as seen from `named_from`."""
    files = await asyncio.to_thread(_resolved_once, paths)
    log.info("loading_files", count=len(files))
    diff_files = await read_text_files(files, named_from=named_from)
    return ReviewOpening(
        mode=ReviewMode.FILES,
        diff_files=diff_files,
        title=_files_title(files),
        # The same files are the same review, in whatever order they are named
        identity="\n".join(sorted(str(file) for file in files)),
        root=None,
        base=None,
    )


async def open_transcript(path: Path) -> ReviewOpening:
    """A conversation, from the JSONL file Claude Code keeps it in."""
    conversation = await asyncio.to_thread(path.resolve)
    log.info("loading_transcript", path=str(conversation))
    diff_files = await read_transcript(conversation)
    return ReviewOpening(
        mode=ReviewMode.TRANSCRIPT,
        diff_files=diff_files,
        title=f"Conversation {conversation.stem}",
        identity=f"{conversation}\n{ReviewMode.TRANSCRIPT}",
        root=None,
        base=None,
    )


def _resolved_once(paths: list[Path]) -> list[Path]:
    """Each path resolved, a file named twice kept once, in the order it was first named."""
    return list(dict.fromkeys(path.resolve() for path in paths))


def _diff_title(root: Path, base: str | None) -> str:
    """Name the repository under review and what it is compared against."""
    against = f"changes since {base}" if base else "uncommitted changes"
    return f"{root.name or root}: {against}"


def _files_title(paths: list[Path]) -> str:
    """Name the files under review, so two sets of them are told apart."""
    names = sorted(path.name for path in paths)
    named = ", ".join(names[:FILES_NAMED_IN_TITLE])
    unnamed = len(names) - FILES_NAMED_IN_TITLE
    return f"{named} + {unnamed} more" if unnamed > 0 else named

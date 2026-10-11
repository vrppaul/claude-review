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

from claude_review.domain.exceptions import UnknownVersionError
from claude_review.domain.interfaces import Repository
from claude_review.domain.models import HEAD, DiffFile, ReviewMode
from claude_review.services.diff_reading import read_diff
from claude_review.services.text_files import read_text_files
from claude_review.services.transcript import read_transcript

log = structlog.get_logger()

# How many files a files review names in its title before it counts the rest
FILES_NAMED_IN_TITLE = 3


class OpenedRepository(BaseModel):
    """The repository a diff review reads from, and what its working tree is compared against."""

    model_config = ConfigDict(frozen=True)

    root: Path
    # The base as the reader named it — `HEAD~1`, `main` — or None for the
    # uncommitted changes. The review is named by it, never by an id.
    named_base: str | None
    # What every take of the diff is read against: the commit the base named
    # as the review opened — HEAD's, for the uncommitted changes — or the
    # empty tree, in a repository with nothing committed. A name moves with
    # every commit, and the agent commits as it works: read against the name,
    # the review would lose the work under review, and its threads with it.
    pinned_base: str


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
    # Where a diff review reads from; a review of files or of a conversation
    # has no repository
    repository: OpenedRepository | None

    @property
    def opened_against(self) -> str | None:
        """The base as the reader named it: None for the uncommitted changes, and for a review of no repository."""
        return self.repository.named_base if self.repository is not None else None


async def open_diff(location: Path, base: str | None, repository: Repository) -> ReviewOpening:
    """The changes in the repository `location` is in, against `base`, or uncommitted ones without it.

    Git reports paths relative to the repository root rather than to the
    directory it was run in, so the review is told the root, not `location`:
    anything that reads those paths later — expanding a hunk's context — has
    to start there.

    Raises:
        UnknownVersionError: if `base` names no commit of the repository.
    """
    resolved_location = await asyncio.to_thread(location.resolve)
    log.info("loading_diff", path=str(resolved_location), base=base)
    async with repository.staged(resolved_location) as staged:
        pinned_base = await _pinned_base(repository, resolved_location, base)
        diff_files = await read_diff(staged, base=pinned_base, ignore_whitespace=False)
    root = await repository.top_level(resolved_location) or resolved_location
    return ReviewOpening(
        mode=ReviewMode.DIFF,
        diff_files=diff_files,
        title=_diff_title(root, base),
        identity=f"{root}\n{base or ''}",
        repository=OpenedRepository(root=root, named_base=base, pinned_base=pinned_base),
    )


async def _pinned_base(repository: Repository, location: Path, base: str | None) -> str:
    """What the base names as the review opens: the commit, or the empty tree when nothing is committed.

    Raises:
        UnknownVersionError: if the base the reader named is no commit.
    """
    commit = await repository.commit_named(location, base or HEAD)
    if commit is not None:
        return commit
    if base is None:
        return await repository.empty_tree(location)
    msg = f"{base} is not a commit of this repository"
    raise UnknownVersionError(msg)


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
        repository=None,
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
        repository=None,
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

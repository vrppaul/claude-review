"""What a review opens on: its content, read once, and what names it.

Each kind of review reads its content its own way, and names itself its own
way; everything after that — the port, the server, the way out — is the
same for all three. Paths are resolved here, before anything else: what
makes two openings the same review is where the files are, not how they
were named.
"""

import asyncio
import hashlib
from pathlib import Path
from typing import Annotated, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field

from claude_review.domain.exceptions import UnknownVersionError
from claude_review.domain.interfaces import Repository
from claude_review.domain.models import (
    HEAD,
    Checkout,
    DiffFile,
    InRepository,
    OfConversation,
    OfFiles,
    RepositoryAt,
    ReviewMode,
    WhereTheChangeIs,
)
from claude_review.services.diff_reading import read_diff
from claude_review.services.text_files import read_text_files
from claude_review.services.transcript import SHORT_ID_LENGTH, read_transcript

log = structlog.get_logger()

# How many files a files review names in its title before it counts the rest
FILES_NAMED_IN_TITLE = 3

# What each kind of review is called in its header: a repository's changes,
# against what they are compared; files, by their names; a conversation, by
# the short id of the session it is
DIFF_TITLE = "{repository}: {against}"
SINCE_A_BASE = "changes since {base}"
UNCOMMITTED = "uncommitted changes"
FILE_NAMES_SEPARATOR = ", "
MORE_FILES = "{named} + {unnamed} more"
CONVERSATION_TITLE = "Conversation {name}"
# What parts the pieces an identity is made of: no path holds a line break
IDENTITY_SEPARATOR = "\n"
# How long a digest of an identity is, in bytes: far more than enough to tell
# apart every review one reader ever opens
IDENTITY_DIGEST_BYTES = 16
# What a diff of the uncommitted changes adds to its root in its identity: no base
NO_BASE = ""


class OpenedRepository(BaseModel):
    """The repository a diff review reads from, what its tree is compared against, and what it had checked out."""

    model_config = ConfigDict(frozen=True)

    kind: Literal[ReviewMode.DIFF] = ReviewMode.DIFF
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
    # What its working tree had checked out as the review opened: the branch,
    # or the commit on none
    checkout: Checkout

    @property
    def name(self) -> str:
        """What the repository is called: its root's name, or the whole path where the root has none, as `/` does."""
        return self.root.name or str(self.root)

    @property
    def where(self) -> InRepository:
        """Where the change is, as the header says it: the repository, by its name, and what it had checked out."""
        return InRepository(repository=RepositoryAt(name=self.name, checkout=self.checkout))


# What a review opens on, one kind to each kind of review: a repository's change, read from it whenever it is
# taken again; or files or a conversation, read once
type OpenedSource = Annotated[OpenedRepository | OfFiles | OfConversation, Field(discriminator="kind")]


class ReviewOpening(BaseModel):
    """What a review opens on, read and named."""

    model_config = ConfigDict(frozen=True)

    source: OpenedSource
    diff_files: list[DiffFile]
    # What the header says is under review
    title: str
    # What makes it the same review when it is opened again: that lands it on
    # the same port, and its page on the draft its reader left in it
    identity: str

    @property
    def mode(self) -> ReviewMode:
        """What kind of review it is: the kind of what it opens on."""
        return self.source.kind

    @property
    def identity_digest(self) -> str:
        """The identity in short, a name that says nothing of the paths it is made of: how a page knows its review."""
        return hashlib.blake2s(self.identity.encode(), digest_size=IDENTITY_DIGEST_BYTES).hexdigest()

    @property
    def opened_against(self) -> str | None:
        """The base as the reader named it: None for the uncommitted changes, and for a review of no repository."""
        match self.source:
            case OpenedRepository(named_base=named_base):
                return named_base
            case OfFiles() | OfConversation():
                return None

    @property
    def where(self) -> WhereTheChangeIs:
        """Where the change under review is: in its repository, or in the files or the conversation read."""
        match self.source:
            case OpenedRepository() as repository:
                return repository.where
            case OfFiles() | OfConversation() as read_once:
                return read_once


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
    opened = OpenedRepository(
        root=root,
        named_base=base,
        pinned_base=pinned_base,
        checkout=await repository.checked_out(resolved_location),
    )
    return ReviewOpening(
        source=opened,
        diff_files=diff_files,
        title=_diff_title(opened.name, base),
        identity=IDENTITY_SEPARATOR.join((str(root), base or NO_BASE)),
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
        source=OfFiles(),
        diff_files=diff_files,
        title=_files_title(files),
        # The same files are the same review, in whatever order they are named
        identity=IDENTITY_SEPARATOR.join(sorted(str(file) for file in files)),
    )


async def open_transcript(path: Path) -> ReviewOpening:
    """A conversation, from the JSONL file Claude Code keeps it in."""
    conversation = await asyncio.to_thread(path.resolve)
    log.info("loading_transcript", path=str(conversation))
    transcript = await read_transcript(conversation)
    return ReviewOpening(
        source=OfConversation(),
        diff_files=transcript.turns,
        title=CONVERSATION_TITLE.format(name=transcript.session_id[:SHORT_ID_LENGTH]),
        identity=IDENTITY_SEPARATOR.join((str(conversation), ReviewMode.TRANSCRIPT)),
    )


def _resolved_once(paths: list[Path]) -> list[Path]:
    """Each path resolved, a file named twice kept once, in the order it was first named."""
    return list(dict.fromkeys(path.resolve() for path in paths))


def changes_since(base: str | None) -> str:
    """What a diff against `base` shows, in words: the uncommitted changes when there is no base.

    The words of the review's title and of the bases its page offers, written
    once for both.
    """
    return SINCE_A_BASE.format(base=base) if base else UNCOMMITTED


def _diff_title(repository_name: str, base: str | None) -> str:
    """Name the repository under review and what it is compared against."""
    return DIFF_TITLE.format(repository=repository_name, against=changes_since(base))


def _files_title(paths: list[Path]) -> str:
    """Name the files under review, so two sets of them are told apart."""
    names = sorted(path.name for path in paths)
    named = FILE_NAMES_SEPARATOR.join(names[:FILES_NAMED_IN_TITLE])
    unnamed = len(names) - FILES_NAMED_IN_TITLE
    return MORE_FILES.format(named=named, unnamed=unnamed) if unnamed > 0 else named

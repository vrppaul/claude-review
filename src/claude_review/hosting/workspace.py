"""Where a review keeps what it writes: its own temporary directories, and what it remembers about its reader."""

import asyncio
import contextlib
import os
import stat
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

from pydantic import BaseModel

from claude_review.hosting.announcer import ReviewAnnouncer
from claude_review.hosting.errors import WorkspaceRefusedError

# Where every review of one user keeps what it kept of itself, in the system's
# temporary directory: named by the user's id, so each user has one
KEPT_BY_EVERY_REVIEW = "claude-review-{user}"
# Who may enter it: the user alone, since what a review keeps holds copies of
# files nobody committed; and what of its mode would let anybody else in
ONLY_THE_USER = 0o700
REACHABLE_BY_OTHERS = stat.S_IRWXG | stat.S_IRWXO
# What a review keeps of itself, in its own directory there
RECORD_FILE = "review.json"
# Where in that directory the trees a review of a repository writes down are kept
OBJECTS_DIRECTORY = "objects"
# What the directory of a review's pasted images is called, so it can be told apart in /tmp
IMAGES_SUFFIX = ".claude-review-images"

# Where every review on the machine keeps what it remembers about its reader,
# by the XDG base directory rules: the reader's choices with configuration,
# what the review noticed with state
CONFIG_HOME_VARIABLE = "XDG_CONFIG_HOME"
STATE_HOME_VARIABLE = "XDG_STATE_HOME"
CONFIG_HOME_FALLBACK = Path(".config")
STATE_HOME_FALLBACK = Path(".local") / "state"
READER_DIRECTORY = "claude-review"
SETTINGS_FILE = "settings.json"
GUIDE_FILE = "guide.json"


class ReviewWorkspace(BaseModel):
    """Where a review writes, so nothing of it lands in the repository under review."""

    # Where the review keeps what it finds again if it is opened again before
    # its reader finishes it: its record, and the trees
    kept: Path
    # Where the trees written down at every take of the diff are kept. None
    # in a review whose content did not come from a repository: it leaves no
    # marks, and so cannot offer its own rounds as bases.
    objects: Path | None
    # Where the images the reader pastes into the panel are kept
    images: Path

    @property
    def record(self) -> Path:
        """What the review keeps of itself: its round, and its story."""
        return self.kept / RECORD_FILE


class ReaderFiles(BaseModel):
    """Where what a review remembers about its reader is kept, for every review.

    Two files for two kinds of thing: what the reader chose, kept with their
    configuration, and what the review noticed, kept with other programs'
    state. Configuration is often kept in git, where a release number
    changing with every upgrade would be noise.
    """

    settings: Path
    guide: Path


@contextlib.asynccontextmanager
async def review_workspace(
    identity: str, *, writes_trees: bool, announcer: ReviewAnnouncer
) -> AsyncGenerator[ReviewWorkspace]:
    """Lend the review of this identity, named in short, the directories it writes to while it runs.

    Two, because they outlive the review differently. What the review keeps
    of itself, and the trees a review of a repository writes down at every
    take, stay in a directory named by its identity: stopped under its reader
    and opened again on the same change, it is the same review, and finds
    there its round, its story, and the trees that story is followed from,
    until its reader finishes it (`forget_review`). The trees hold a copy of
    every untracked file, so every review of the user keeps its own in a
    directory only the user can enter. They go when the system clears its
    temporary directory, on its own schedule.

    The images handed to the agent stay; the review drops the rest before it
    lets the workspace go. The last round names them, and the agent reads it
    only once the review has ended. Whoever started the review is told where
    they are; if none was sent, no directory of images is left.

    Raises:
        WorkspaceRefusedError: if where every review of the user keeps its own is not a directory of the user's.
    """
    workspace = await asyncio.to_thread(_workspace_of, identity, writes_trees=writes_trees)
    try:
        yield workspace
    finally:
        if await asyncio.to_thread(_left_if_written_into, workspace.images):
            announcer.images_left_in(workspace.images)


async def forget_review(workspace: ReviewWorkspace) -> None:
    """Remove the record a review kept of itself once its reader finished it: the same change opened then is new.

    The record alone: the trees are of no use to a new review but take
    nothing from it, and another review of the same change, opened beside
    this one, may still be reading them.
    """
    await asyncio.to_thread(workspace.record.unlink, missing_ok=True)


def reader_files() -> ReaderFiles:
    """Where this machine's reviews keep what they remember about their reader."""
    config = _base_directory(CONFIG_HOME_VARIABLE, CONFIG_HOME_FALLBACK)
    state = _base_directory(STATE_HOME_VARIABLE, STATE_HOME_FALLBACK)
    return ReaderFiles(
        settings=config / READER_DIRECTORY / SETTINGS_FILE,
        guide=state / READER_DIRECTORY / GUIDE_FILE,
    )


def _workspace_of(identity: str, *, writes_trees: bool) -> ReviewWorkspace:
    """The directories of the review of this identity, made or found again, and a new one for its images.

    Raises:
        WorkspaceRefusedError: if where every review of the user keeps its own is not a directory of the user's.
    """
    kept = _directory_in(_kept_by_every_review(), identity)
    return ReviewWorkspace(
        kept=kept,
        objects=_directory_in(kept, OBJECTS_DIRECTORY) if writes_trees else None,
        images=Path(tempfile.mkdtemp(suffix=IMAGES_SUFFIX)),
    )


def _kept_by_every_review() -> Path:
    """The directory every review of the user keeps its own in: made for the user alone, or found to be theirs.

    Its name is one anybody on the machine can work out, so another user may
    have made it first, or left a link in its place to a directory of their
    own; and one found open to others may hold what they put there. Each is
    refused, and nothing is written there.

    Raises:
        WorkspaceRefusedError: if it is a link, anything but a directory of the user's, or open to others.
    """
    user = os.getuid()
    directory = Path(tempfile.gettempdir()) / KEPT_BY_EVERY_REVIEW.format(user=user)
    with contextlib.suppress(FileExistsError):
        directory.mkdir(mode=ONLY_THE_USER)
    found = directory.lstat()
    if not stat.S_ISDIR(found.st_mode) or found.st_uid != user or found.st_mode & REACHABLE_BY_OTHERS:
        msg = f"{directory} is not a directory only you can enter: set TMPDIR to one that is"
        raise WorkspaceRefusedError(msg)
    return directory


def _directory_in(parent: Path, name: str) -> Path:
    """A directory of this name in another, made unless it is there already."""
    directory = parent / name
    directory.mkdir(exist_ok=True)
    return directory


def _left_if_written_into(directory: Path) -> bool:
    """Leave a directory something was written into, remove one nothing was, and say whether it was left."""
    if any(directory.iterdir()):
        return True
    directory.rmdir()
    return False


def _base_directory(variable: str, fallback: Path) -> Path:
    """A base directory the environment names, or its usual place in the home directory.

    The rules ignore a relative path in the variable: it would point somewhere
    different from every directory a review is started in.
    """
    named = os.environ.get(variable, "")
    return Path(named) if Path(named).is_absolute() else Path.home() / fallback

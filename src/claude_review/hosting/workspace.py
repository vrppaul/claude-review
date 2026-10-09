"""Where a review keeps what it writes: its own temporary directories, and what it remembers about its reader."""

import contextlib
import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import click

from claude_review.domain.models import ReaderFiles, ReviewWorkspace

# What a review's own temporary directories are called, so they can be told apart in /tmp
OBJECTS_SUFFIX = ".claude-review-objects"
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


@contextlib.contextmanager
def review_workspace(*, writes_trees: bool) -> Generator[ReviewWorkspace]:
    """Lend the review the directories it writes to while it runs.

    Two, because they outlive the review differently. The trees a review of
    a repository writes at every round go with it: the blob staging writes a
    copy of every untracked file, and it must neither reach the repository
    under review nor be left behind. They are removed here rather than where
    the serving ends, because a review can fail to start after the first tree
    is already written — a port already taken is the ordinary way.

    The images pasted into it stay. The last round names them, and the agent
    reads it only once the review has ended; the system clears its temporary
    directory on its own schedule, which is long enough for that.
    """
    images = Path(tempfile.mkdtemp(suffix=IMAGES_SUFFIX))
    objects = Path(tempfile.mkdtemp(suffix=OBJECTS_SUFFIX)) if writes_trees else None
    try:
        yield ReviewWorkspace(objects=objects, images=images)
    finally:
        if objects is not None:
            shutil.rmtree(objects, ignore_errors=True)
        _leave_images(images)


def _leave_images(images: Path) -> None:
    """Leave what was pasted for the agent, and say where; leave nothing if nothing was."""
    if any(images.iterdir()):
        click.echo(
            f"Images pasted in this review stay in {images} until the system clears its temporary files.", err=True
        )
    else:
        images.rmdir()


def reader_files() -> ReaderFiles:
    """Where this machine's reviews keep what they remember about their reader."""
    config = _base_directory(CONFIG_HOME_VARIABLE, CONFIG_HOME_FALLBACK)
    state = _base_directory(STATE_HOME_VARIABLE, STATE_HOME_FALLBACK)
    return ReaderFiles(
        settings=config / READER_DIRECTORY / SETTINGS_FILE,
        guide=state / READER_DIRECTORY / GUIDE_FILE,
    )


def _base_directory(variable: str, fallback: Path) -> Path:
    """A base directory the environment names, or its usual place in the home directory.

    The rules ignore a relative path in the variable: it would point somewhere
    different from every directory a review is started in.
    """
    named = os.environ.get(variable, "")
    return Path(named) if Path(named).is_absolute() else Path.home() / fallback

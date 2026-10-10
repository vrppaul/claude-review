"""The reader's own git settings do not change the diff the review reads.

Git takes settings from the repository, the reader's home and the
environment as well as from its command line, and some of them change how a
diff is written or which repository is read. The review reads one format —
a blank line of context marked as context, git's own three lines of context
around a change, a file as it is stored, a copy as the new file it is — from
the repository it was opened on.
"""

from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from claude_review.domain.models import DiffFile, DiffLine, FileStatus
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_reading import read_diff
from tests.helpers import added_line, context_line, git, removed_line, write_files

# A file with a blank line in it, and the line below the blank that changes
REVIEWED_FILE = "notes.txt"
COMMITTED_LINES = ["first", "", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth"]
CHANGED_NUMBER = 5
CHANGED_TO = "FIFTH"
CHANGED_LINES = [CHANGED_TO if number == CHANGED_NUMBER else line for number, line in enumerate(COMMITTED_LINES, 1)]
# The hunk git writes for that change with nothing set: three lines either side, the blank among them
DEFAULT_HUNK = [
    context_line(2, 2, ""),
    context_line(3, 3, "third"),
    context_line(4, 4, "fourth"),
    removed_line(CHANGED_NUMBER, "fifth"),
    added_line(CHANGED_NUMBER, CHANGED_TO),
    context_line(6, 6, "sixth"),
    context_line(7, 7, "seventh"),
    context_line(8, 8, "eighth"),
]
# A copy of the reviewed file as it now stands, made in the same change
COPIED_FILE = "copied.txt"
# Where git's attributes name the diff driver a file is shown with
ATTRIBUTES_FILE = ".gitattributes"


class ReaderSetup(BaseModel):
    """What the reader has set: git's settings, the attributes that bring them to bear on a file, the environment."""

    settings: dict[str, str] = Field(default_factory=dict)
    attributes: str = ""
    environment: dict[str, str] = Field(default_factory=dict)


# Each way a reader's own setup could reshape a diff, by what it does
READER_SETUPS = {
    "a blank line of context written bare": ReaderSetup(settings={"diff.suppressBlankEmpty": "true"}),
    "no context around a change": ReaderSetup(settings={"diff.context": "0"}),
    "the diff's options in the environment": ReaderSetup(environment={"GIT_DIFF_OPTS": "-u0"}),
    "a converter of the reader's for the file": ReaderSetup(
        settings={"diff.converted.textconv": "sed s/^/converted:/"},
        attributes=f"{REVIEWED_FILE} diff=converted\n",
    ),
}


def _written(lines: list[str]) -> str:
    return "".join(f"{line}\n" for line in lines)


def _committed(repo: Path, attributes: str) -> None:
    """The reviewed file committed, with the attributes when there are any, so they are not a change themselves."""
    write_files(
        repo, {REVIEWED_FILE: _written(COMMITTED_LINES), **({ATTRIBUTES_FILE: attributes} if attributes else {})}
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "notes")


async def _diff(repo: Path) -> list[DiffFile]:
    async with GitRepository(objects=None).staged(repo) as staged:
        return await read_diff(staged, base=None, ignore_whitespace=False)


async def _hunk_lines(repo: Path) -> list[DiffLine]:
    [changed] = await _diff(repo)
    [hunk] = changed.hunks
    return hunk.lines


@pytest.mark.parametrize("setup", list(READER_SETUPS.values()), ids=list(READER_SETUPS))
async def test_a_setting_of_the_readers_own_leaves_the_reviews_hunk_as_git_writes_it_by_default(
    tmp_git_repo: Path, setup: ReaderSetup, monkeypatch: pytest.MonkeyPatch
) -> None:
    _committed(tmp_git_repo, setup.attributes)
    write_files(tmp_git_repo, {REVIEWED_FILE: _written(CHANGED_LINES)})
    for key, value in setup.settings.items():
        git(tmp_git_repo, "config", key, value)
    for name, value in setup.environment.items():
        monkeypatch.setenv(name, value)

    assert await _hunk_lines(tmp_git_repo) == DEFAULT_HUNK


async def test_a_copy_is_read_as_the_new_file_it_is_whatever_the_reader_detects(tmp_git_repo: Path) -> None:
    """Read as changes to the file it was copied from, its lines would be numbered as another file's."""
    _committed(tmp_git_repo, attributes="")
    write_files(tmp_git_repo, {REVIEWED_FILE: _written(CHANGED_LINES), COPIED_FILE: _written(CHANGED_LINES)})
    git(tmp_git_repo, "config", "diff.renames", "copies")

    copy = next(changed for changed in await _diff(tmp_git_repo) if changed.path == COPIED_FILE)

    assert copy.status == FileStatus.ADDED
    assert [line for hunk in copy.hunks for line in hunk.lines] == [
        added_line(number, line) for number, line in enumerate(CHANGED_LINES, 1)
    ]


async def test_the_review_reads_the_repository_it_was_opened_on_wherever_the_environment_points_git(
    tmp_git_repo: Path, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A review started from a git hook inherits the hook's GIT_DIR and GIT_INDEX_FILE."""
    _committed(tmp_git_repo, attributes="")
    write_files(tmp_git_repo, {REVIEWED_FILE: _written(CHANGED_LINES)})
    elsewhere = tmp_path_factory.mktemp("elsewhere")
    git(elsewhere, "init", "-b", "main")
    monkeypatch.setenv("GIT_DIR", str(elsewhere / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(elsewhere / ".git" / "index"))

    assert await _hunk_lines(tmp_git_repo) == DEFAULT_HUNK

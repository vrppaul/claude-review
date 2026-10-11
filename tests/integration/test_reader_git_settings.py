"""The reader's own git settings do not change what the review reads.

Git takes settings from the repository, the reader's home and the
environment as well as from its command line, and some of them change how a
diff is written, which repository or index is read, or how a path is
matched. The review reads one format — git's own three lines of context
around a change, a file as it is stored, a copy as the new file it is, a
submodule as the commit it moved to — from the repository it was opened on,
and a path it names is that path.
"""

from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from claude_review.domain.models import HEAD, DiffFile, DiffLine, FileStatus
from claude_review.repositories.git_repository import FOREIGN_GIT_VARIABLES, GitRepository
from claude_review.services.diff_reading import read_diff
from tests.helpers import GIT_YES, added_line, context_line, git, removed_line, write_files

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
# A file another repository tracks and the reviewed one does not
SECRET_FILE = ".env"
SECRET_TEXT = "TOKEN=1\n"
# A tracked file, and an untracked one whose name read as a pattern would match it
TRACKED_FILE = "a.py"
PATTERN_NAMED_FILE = "[ab].py"
# The ways of matching a path a reader may set for every git they run, which git refuses beside a literal path
MATCHING_VARIABLES = ["GIT_GLOB_PATHSPECS", "GIT_ICASE_PATHSPECS"]
# Where the submodule sits, what it holds, and the setting that would show it as its own files
SUBMODULE_PATH = "sub"
SUBMODULE_FILE = "inside.txt"
# Who commits in the repositories a test makes beside the reviewed one
AUTHOR_SETTINGS = ["-c", "user.email=test@test.com", "-c", "user.name=Test"]


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
        return await read_diff(staged, base=HEAD, ignore_whitespace=False)


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

    assert await _hunk_lines(tmp_git_repo) == DEFAULT_HUNK


async def test_an_inherited_index_does_not_decide_what_the_repository_keeps(
    tmp_git_repo: Path, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read from another repository's index, an untracked secret would pass for kept, and its lines could be read."""
    elsewhere = tmp_path_factory.mktemp("elsewhere")
    git(elsewhere, "init", "-b", "main")
    write_files(elsewhere, {SECRET_FILE: SECRET_TEXT})
    git(elsewhere, "add", SECRET_FILE)
    write_files(tmp_git_repo, {SECRET_FILE: SECRET_TEXT})
    monkeypatch.setenv("GIT_INDEX_FILE", str(elsewhere / ".git" / "index"))

    assert await GitRepository(objects=None).is_tracked(tmp_git_repo, SECRET_FILE) is False


def test_every_variable_git_reads_its_repository_by_is_left_out(tmp_git_repo: Path) -> None:
    """A newer git that names one more fails here, rather than being let through unseen."""
    named = set(git(tmp_git_repo, "rev-parse", "--local-env-vars").split())

    assert named <= FOREIGN_GIT_VARIABLES


async def test_a_path_the_review_names_is_that_path_never_a_pattern(tmp_git_repo: Path) -> None:
    """Read as a pattern, an untracked file's name would match the tracked file it resembles."""
    write_files(tmp_git_repo, {TRACKED_FILE: _written(COMMITTED_LINES)})
    git(tmp_git_repo, "add", TRACKED_FILE)
    git(tmp_git_repo, "commit", "-m", "tracked")
    write_files(tmp_git_repo, {PATTERN_NAMED_FILE: SECRET_TEXT})

    assert await GitRepository(objects=None).is_tracked(tmp_git_repo, PATTERN_NAMED_FILE) is False


@pytest.mark.parametrize("matching", MATCHING_VARIABLES)
async def test_how_the_reader_matches_paths_does_not_stop_git(
    tmp_git_repo: Path, matching: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Git refuses to run with a literal path and another way of matching both set."""
    write_files(tmp_git_repo, {TRACKED_FILE: _written(COMMITTED_LINES)})
    git(tmp_git_repo, "add", TRACKED_FILE)
    git(tmp_git_repo, "commit", "-m", "tracked")
    monkeypatch.setenv(matching, GIT_YES)

    assert await GitRepository(objects=None).is_tracked(tmp_git_repo, TRACKED_FILE) is True


async def test_a_submodule_is_read_as_the_commit_it_moved_to(
    tmp_git_repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Shown as its own files, a submodule would put files in the review that the repository does not hold."""
    inner = tmp_path_factory.mktemp("inner")
    git(inner, "init", "-b", "main")
    write_files(inner, {SUBMODULE_FILE: "first\n"})
    git(inner, "add", SUBMODULE_FILE)
    git(inner, *AUTHOR_SETTINGS, "commit", "-m", "first")
    git(tmp_git_repo, "-c", "protocol.file.allow=always", "submodule", "add", str(inner), SUBMODULE_PATH)
    git(tmp_git_repo, "commit", "-m", "submodule")
    moved = tmp_git_repo / SUBMODULE_PATH
    write_files(moved, {SUBMODULE_FILE: "second\n"})
    git(moved, *AUTHOR_SETTINGS, "commit", "-am", "second")
    git(tmp_git_repo, "config", "diff.submodule", "diff")

    assert [changed.path for changed in await _diff(tmp_git_repo)] == [SUBMODULE_PATH]

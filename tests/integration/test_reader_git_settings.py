"""The reader's own git settings do not change the diff the review reads.

Git takes settings from the repository and the reader's home as well as from
its command line, and some of them change how a diff is written. The review
reads one format: a blank line of context marked as context, and git's own
three lines of context around a change, which the page counts its hidden
lines by.
"""

from pathlib import Path

import pytest

from claude_review.domain.models import DiffLine
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_reading import read_diff
from tests.helpers import added_line, context_line, git, removed_line

# A file with a blank line in it, and the line below the blank that changes
REVIEWED_FILE = "notes.txt"
COMMITTED_LINES = ["first", "", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth"]
CHANGED_NUMBER = 5
CHANGED_TO = "FIFTH"
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


def _written(lines: list[str]) -> str:
    return "".join(f"{line}\n" for line in lines)


async def _hunk_lines(repo: Path) -> list[DiffLine]:
    async with GitRepository(objects=None).staged(repo) as staged:
        [changed] = await read_diff(staged, base=None, ignore_whitespace=False)
    [hunk] = changed.hunks
    return hunk.lines


@pytest.mark.parametrize(
    ("setting", "value"),
    [
        pytest.param("diff.suppressBlankEmpty", "true", id="a blank line of context written bare"),
        pytest.param("diff.context", "0", id="no context around a change"),
    ],
)
async def test_a_setting_of_the_readers_own_leaves_the_reviews_hunk_as_git_writes_it_by_default(
    tmp_git_repo: Path, setting: str, value: str
) -> None:
    (tmp_git_repo / REVIEWED_FILE).write_text(_written(COMMITTED_LINES))
    git(tmp_git_repo, "add", REVIEWED_FILE)
    git(tmp_git_repo, "commit", "-m", "notes")
    changed = [CHANGED_TO if number == CHANGED_NUMBER else line for number, line in enumerate(COMMITTED_LINES, 1)]
    (tmp_git_repo / REVIEWED_FILE).write_text(_written(changed))
    git(tmp_git_repo, "config", setting, value)

    assert await _hunk_lines(tmp_git_repo) == DEFAULT_HUNK

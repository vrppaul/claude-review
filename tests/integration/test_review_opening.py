"""What a review opens on, and what names it: the title its header shows and the identity its port comes from."""

from pathlib import Path

import pytest

from claude_review.domain.models import ReviewMode
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.review_opening import open_diff, open_files, open_transcript

# More files than a title names before it counts the rest
FIVE_FILES = ("e.md", "d.md", "c.md", "b.md", "a.md")


@pytest.fixture
def changed_repo(tmp_git_repo: Path) -> Path:
    (tmp_git_repo / "initial.txt").write_text("changed\n")
    return tmp_git_repo


def _written(directory: Path, *names: str) -> list[Path]:
    """Files with something in them, so there is something to review."""
    for name in names:
        (directory / name).write_text(f"{name}\n")
    return [directory / name for name in names]


async def test_a_diff_is_named_by_its_repository_and_what_it_is_compared_against(changed_repo: Path) -> None:
    uncommitted = await open_diff(changed_repo, None, GitRepository(objects=None))
    since_a_commit = await open_diff(changed_repo, "HEAD", GitRepository(objects=None))

    assert uncommitted.title == f"{changed_repo.name}: uncommitted changes"
    assert since_a_commit.title == f"{changed_repo.name}: changes since HEAD"


async def test_a_diff_opened_from_a_subdirectory_is_the_whole_repository(changed_repo: Path) -> None:
    """The diff is the repository's whatever directory it was opened from, and so are its name and its port."""
    nested = changed_repo / "sub"
    nested.mkdir()

    from_inside = await open_diff(nested, None, GitRepository(objects=None))
    from_the_root = await open_diff(changed_repo, None, GitRepository(objects=None))

    assert from_inside.root == from_the_root.root
    assert from_inside.title == from_the_root.title
    assert from_inside.identity == from_the_root.identity


async def test_a_diff_against_another_base_is_another_review(changed_repo: Path) -> None:
    """Its threads are about other changes, and its draft must not be mixed with this one's."""
    assert (await open_diff(changed_repo, None, GitRepository(objects=None))).identity != (
        await open_diff(changed_repo, "HEAD", GitRepository(objects=None))
    ).identity


async def test_files_are_named_by_what_was_opened(tmp_path: Path) -> None:
    opened = await open_files(_written(tmp_path, "b.py", "a.md"))

    assert opened.mode == ReviewMode.FILES
    assert opened.title == "a.md, b.py"


async def test_many_files_are_named_by_the_first_few_and_counted_after(tmp_path: Path) -> None:
    opened = await open_files(_written(tmp_path, *FIVE_FILES))

    assert opened.title == "a.md, b.md, c.md + 2 more"


async def test_the_same_files_in_another_order_are_the_same_review(tmp_path: Path) -> None:
    files = _written(tmp_path, "a.md", "b.md")

    assert (await open_files(files)).identity == (await open_files(files[::-1])).identity


async def test_files_that_start_alike_are_a_different_review(tmp_path: Path) -> None:
    """Same first file, same count: still another set of files, and another draft."""
    first, second, third = _written(tmp_path, "a.md", "b.md", "c.md")

    assert (await open_files([first, second])).identity != (await open_files([first, third])).identity


async def test_a_conversation_is_named_by_its_file(tmp_path: Path) -> None:
    conversation = tmp_path / "abc123.jsonl"
    conversation.write_text("")

    opened = await open_transcript(conversation)

    assert opened.mode == ReviewMode.TRANSCRIPT
    assert opened.title == "Conversation abc123"

"""What a review opens on, and what names it: the title its header shows and the identity its port comes from."""

from pathlib import Path

import pytest

from claude_review.domain.exceptions import UnknownVersionError
from claude_review.domain.models import OnBranch, OnCommit, RepositoryAt, ReviewMode
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.review_opening import open_diff, open_files, open_transcript
from tests.helpers import DEFAULT_BRANCH, INITIAL_FILE, INITIAL_FILES, committed_repository, git

# More files than a title names before it counts the rest
FIVE_FILES = ("e.md", "d.md", "c.md", "b.md", "a.md")
# A branch the change is made on, and how short git writes a commit's id in a repository this small
FEATURE_BRANCH = "feature/where-the-change-is"
SHORT_ID_LENGTH = 7
# A ref HEAD may point at outside the branches: a remote's, whose name git says whole
REMOTE_REF = "refs/remotes/origin/main"


@pytest.fixture
def changed_repo(tmp_git_repo: Path) -> Path:
    (tmp_git_repo / INITIAL_FILE).write_text("changed\n")
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


async def test_a_diff_says_the_branch_checked_out_or_on_none_the_commit(tmp_path: Path) -> None:
    """A branch by its whole name, whatever a tag is called, before anything is committed and outside the branches;
    on none, the commit."""
    on_a_branch = committed_repository(tmp_path / "on-a-branch", INITIAL_FILES)
    git(on_a_branch, "switch", "--quiet", "--create", FEATURE_BRANCH)
    beside_a_tag_of_its_name = committed_repository(tmp_path / "beside-a-tag", INITIAL_FILES)
    git(beside_a_tag_of_its_name, "tag", DEFAULT_BRANCH)
    nothing_committed = tmp_path / "nothing-committed"
    nothing_committed.mkdir()
    git(nothing_committed, "init", "--quiet", "--initial-branch", DEFAULT_BRANCH)
    outside_the_branches = committed_repository(tmp_path / "outside-the-branches", INITIAL_FILES)
    git(outside_the_branches, "update-ref", REMOTE_REF, "HEAD")
    git(outside_the_branches, "symbolic-ref", "HEAD", REMOTE_REF)
    on_no_branch = committed_repository(tmp_path / "on-no-branch", INITIAL_FILES)
    git(on_no_branch, "switch", "--quiet", "--detach")
    commit = git(on_no_branch, "rev-parse", "HEAD").strip()

    opened = [
        (await open_diff(repository, None, GitRepository(objects=None))).repository_at
        for repository in (on_a_branch, beside_a_tag_of_its_name, nothing_committed, outside_the_branches, on_no_branch)
    ]

    assert opened == [
        RepositoryAt(name=on_a_branch.name, checkout=OnBranch(branch=FEATURE_BRANCH)),
        RepositoryAt(name=beside_a_tag_of_its_name.name, checkout=OnBranch(branch=DEFAULT_BRANCH)),
        RepositoryAt(name=nothing_committed.name, checkout=OnBranch(branch=DEFAULT_BRANCH)),
        RepositoryAt(name=outside_the_branches.name, checkout=OnBranch(branch=REMOTE_REF)),
        RepositoryAt(name=on_no_branch.name, checkout=OnCommit(commit=commit[:SHORT_ID_LENGTH])),
    ]


async def test_a_diff_opened_from_a_subdirectory_is_the_whole_repository(changed_repo: Path) -> None:
    """The diff is the repository's whatever directory it was opened from, and so are its name and its port."""
    nested = changed_repo / "sub"
    nested.mkdir()

    from_inside = await open_diff(nested, None, GitRepository(objects=None))
    from_the_root = await open_diff(changed_repo, None, GitRepository(objects=None))

    assert from_inside.repository == from_the_root.repository
    assert from_inside.title == from_the_root.title
    assert from_inside.identity == from_the_root.identity


async def test_a_diff_opened_from_a_subdirectory_shows_what_changed_outside_it(changed_repo: Path) -> None:
    """A reader whose git writes diffs relative to where it runs would see only the subdirectory's changes."""
    nested = changed_repo / "sub"
    nested.mkdir()
    (nested / "inside.py").write_text("inside\n")
    git(changed_repo, "config", "diff.relative", "true")

    opened = await open_diff(nested, None, GitRepository(objects=None))

    assert sorted(changed.path for changed in opened.diff_files) == [INITIAL_FILE, "sub/inside.py"]


@pytest.mark.parametrize("base", ["no-such-ref", "key-blob"], ids=["nothing-by-that-name", "a-tag-on-a-blob"])
async def test_a_base_that_names_no_commit_is_refused(changed_repo: Path, base: str) -> None:
    """Nothing can be compared against it: refused as what the reader asked for, not failed as git."""
    blob = git(changed_repo, "hash-object", "-w", INITIAL_FILE).strip()
    git(changed_repo, "tag", "-a", "key-blob", blob, "-m", "a key, kept as a tag")

    with pytest.raises(UnknownVersionError, match=base):
        await open_diff(changed_repo, base, GitRepository(objects=None))


async def test_a_diff_against_another_base_is_another_review(changed_repo: Path) -> None:
    """Its threads are about other changes, and its draft must not be mixed with this one's."""
    assert (await open_diff(changed_repo, None, GitRepository(objects=None))).identity != (
        await open_diff(changed_repo, "HEAD", GitRepository(objects=None))
    ).identity


async def test_files_are_named_by_what_was_opened(tmp_path: Path) -> None:
    opened = await open_files(_written(tmp_path, "b.py", "a.md"), named_from=tmp_path)

    assert opened.mode == ReviewMode.FILES
    assert opened.title == "a.md, b.py"


async def test_many_files_are_named_by_the_first_few_and_counted_after(tmp_path: Path) -> None:
    opened = await open_files(_written(tmp_path, *FIVE_FILES), named_from=tmp_path)

    assert opened.title == "a.md, b.md, c.md + 2 more"


async def test_the_same_files_in_another_order_are_the_same_review(tmp_path: Path) -> None:
    files = _written(tmp_path, "a.md", "b.md")

    assert (await open_files(files, named_from=tmp_path)).identity == (
        await open_files(files[::-1], named_from=tmp_path)
    ).identity


async def test_files_that_start_alike_are_a_different_review(tmp_path: Path) -> None:
    """Same first file, same count: still another set of files, and another draft."""
    first, second, third = _written(tmp_path, "a.md", "b.md", "c.md")

    assert (await open_files([first, second], named_from=tmp_path)).identity != (
        await open_files([first, third], named_from=tmp_path)
    ).identity


async def test_a_conversation_is_named_by_its_sessions_short_id(tmp_path: Path) -> None:
    conversation = tmp_path / "63b8ade4-8f1c-4c55-9e4e-0d2a7c1b9f30.jsonl"
    conversation.write_text("")

    opened = await open_transcript(conversation)

    assert opened.mode == ReviewMode.TRANSCRIPT
    assert opened.title == "Conversation 63b8ade4"


async def test_a_file_named_two_ways_is_one_file_and_the_same_review(tmp_path: Path) -> None:
    """However the reader spelled it, a file is reviewed once, and comes back to the same review."""
    [plan] = _written(tmp_path, "plan.md")
    (tmp_path / "sub").mkdir()
    roundabout = tmp_path / "sub" / ".." / "plan.md"

    named_twice = await open_files([plan, roundabout], named_from=tmp_path)

    assert len(named_twice.diff_files) == 1
    assert named_twice.identity == (await open_files([plan], named_from=tmp_path)).identity


async def test_a_conversation_named_by_a_roundabout_path_is_the_same_review(tmp_path: Path) -> None:
    conversation = tmp_path / "abc123.jsonl"
    conversation.write_text("")
    (tmp_path / "sub").mkdir()

    roundabout = await open_transcript(tmp_path / "sub" / ".." / "abc123.jsonl")

    assert roundabout.identity == (await open_transcript(conversation)).identity

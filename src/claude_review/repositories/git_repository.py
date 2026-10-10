import asyncio
import contextlib
import os
import shutil
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import override

import structlog
from pydantic import BaseModel

from claude_review.domain.interfaces import GitError, ReviewedRepository, StagedTree
from claude_review.domain.models import HEAD, GitRef

log = structlog.get_logger()


GIT_TIMEOUT = 30.0
REF_LIMIT = 50
# Git dates a ref in seconds, and the review says every time in milliseconds
MILLISECONDS_PER_SECOND = 1000
# Where the path starts in an entry of `git status --porcelain`
PORCELAIN_PATH_START = 3

# Settings every command runs with, whatever the reader's configuration says:
# a path outside plain ASCII keeps git's own quoting, which the parser decodes
GIT_SETTINGS = ["-c", "core.quotePath=true"]

# What in the environment would point git elsewhere or change what it says,
# inherited from a git hook or the reader's shell: none is passed on, and a
# command sets the ones it means. They are what `git rev-parse
# --local-env-vars` lists, which say which repository, index, object store
# and settings git reads; GIT_DIFF_OPTS, which beats --unified on the
# command line; and the ways of matching a path git refuses to run beside
# the literal one every command sets. A `safe.directory` handed down in
# GIT_CONFIG_PARAMETERS goes with the rest; one in the reader's own
# configuration still holds. What an option of every diff already
# overrides, as --no-ext-diff does an external diff tool, needs no place here.
FOREIGN_GIT_VARIABLES = frozenset(
    {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_CONFIG",
        "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG_COUNT",
        "GIT_OBJECT_DIRECTORY",
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_IMPLICIT_WORK_TREE",
        "GIT_GRAFT_FILE",
        "GIT_INDEX_FILE",
        "GIT_NO_REPLACE_OBJECTS",
        "GIT_REPLACE_REF_BASE",
        "GIT_PREFIX",
        "GIT_SHALLOW_FILE",
        "GIT_COMMON_DIR",
        "GIT_DIFF_OPTS",
        "GIT_GLOB_PATHSPECS",
        "GIT_ICASE_PATHSPECS",
    }
)

# What every command sets: a path the review names is that path, never a
# pattern — "[ab].py" is the file of that name, not a.py beside it
EVERY_COMMAND_SETS = {"GIT_LITERAL_PATHSPECS": "1"}

# How many lines of context a hunk carries: git's own default, so a change is
# shown with what is around it whatever the reader set; the page widens it on
# request
CONTEXT_LINES = 3

# How a diff is written, whatever the reader's configuration says. The parser
# reads one format: a diff tool of the reader's own, colours, other prefixes,
# paths relative to a subdirectory or another amount of context must not
# stand in for it. Nor may the reader's choices of what to show: a file is
# shown as it is stored, never as a converter of theirs renders it, whose
# lines would not be the file's; a copy as the new file it is, never as
# changes to the file it was copied from; a submodule as the commit it moved
# to, never as its log or its own files.
DIFF_STAGED = [
    "diff",
    "--cached",
    "--no-ext-diff",
    "--no-color",
    "--no-relative",
    "--src-prefix=a/",
    "--dst-prefix=b/",
    f"--unified={CONTEXT_LINES}",
    "--find-renames",
    "--no-textconv",
    "--submodule=short",
]

# Ends the options, so a revision that follows can never be read as one
END_OF_OPTIONS = "--end-of-options"

# What the temporary pieces of one staging are called, to be told apart in /tmp
INDEX_SUFFIX = ".git-index"
OBJECTS_SUFFIX = ".git-objects"

# What a repository's own index and object store are called, as `git rev-parse --git-path` asks
INDEX_NAME = "index"
OBJECTS_NAME = "objects"


class GitRun(BaseModel):
    """What one git command said, and how it ended."""

    exit_code: int
    output: str
    errors: str


class OwnPaths(BaseModel):
    """Where a repository keeps its own object store and index."""

    objects: Path
    index: Path


class GitStagedTree(StagedTree):
    """The working tree as it stands, staged whole into an index of one operation's own.

    Everything git is asked within one operation — the diff, the tree written
    down, what changed since earlier trees — reads this one index, so the
    answers agree with each other by construction and the tree is staged
    once rather than once per question. The repository's own index is never
    touched.
    """

    def __init__(self, path: Path, variables: dict[str, str], *, keeps_objects: bool) -> None:
        self._path = path
        self._variables = variables
        self._keeps_objects = keeps_objects

    @override
    async def diff(self, base: str | None, *, ignore_whitespace: bool) -> str:
        """The unified diff from a base to the working tree, untracked files included.

        Without a base, from HEAD: the uncommitted changes. A base may be a
        commit, a ref, or a tree a round was written down as.

        With ignore_whitespace, git leaves out changes that only alter
        whitespace — a reindented block stops hiding the one line that
        actually changed inside it.
        """
        arguments = [*DIFF_STAGED, *(["-w"] if ignore_whitespace else [])]
        if base is not None:
            arguments += [END_OF_OPTIONS, base]
        return await _run(self._path, arguments, self._variables)

    @override
    async def write_tree(self) -> str:
        """Write the tree down and return its id.

        This is how a round leaves a mark. The work under review is
        uncommitted, so between two rounds there may be no commit at all —
        without a tree written here, "what changed since round 2" has nothing
        to be compared against.

        Raises:
            GitError: if the repository throws its objects away, which would
                leave a tree id naming something nobody can read.
        """
        if not self._keeps_objects:
            msg = "a tree written down needs an object store that outlives the staging that wrote it"
            raise GitError(msg)
        return (await _run(self._path, ["write-tree"], self._variables)).strip()

    @override
    async def names_changed_since(self, bases: list[str]) -> dict[str, list[str]]:
        """Which paths differ between each of these bases and the working tree.

        The comparison a diff makes, asked for names alone: what a round
        changed is a list of files, and reading the hunks to find it out
        costs the whole diff. `-z` because git otherwise quotes and escapes
        any path outside plain ASCII, and these are matched against the
        paths already on screen.
        """
        changed: dict[str, list[str]] = {}
        for base in bases:
            try:
                listed = await _run(
                    self._path, [*DIFF_STAGED, "--name-only", "-z", END_OF_OPTIONS, base], self._variables
                )
            except GitError:
                # One base git will not read — a repository with no HEAD, a
                # tree that has been pruned — is one base missing from the
                # answer, not the end of the question
                log.warning("changed_since_refused", base=base)
                continue
            changed[base] = [name for name in listed.split("\0") if name]
        return changed


class GitRepository(ReviewedRepository):
    """The repository under review, asked through the git command line."""

    def __init__(self, *, objects: Path | None) -> None:
        """Take the object store that staging writes to.

        Staging writes a blob for every untracked file, and those do not
        belong in the repository under review — it would otherwise gain one
        per file, and a tree with a large untracked build directory left
        megabytes behind. None throws them away when the staging ends, which
        is all a diff read once needs. A directory given here keeps them for
        as long as it lasts, which is what lets a tree written down be read
        back later: the review owns that directory and takes it with it.
        """
        self._objects = objects

    @override
    @contextlib.asynccontextmanager
    async def staged(self, path: Path) -> AsyncGenerator[GitStagedTree]:
        """Stage the whole working tree into an index of this staging's own, for one operation to read.

        The index starts as a copy of the repository's own, so git knows
        which files it has already read and hashes only what changed: on a
        large tree, milliseconds rather than half a second. Like `git diff`
        and `git status`, it then leaves alone what the reader told git to
        leave alone — a file marked assume-unchanged or skip-worktree. A
        repository with no index of its own starts from HEAD, or from
        nothing.

        The temporary files are made and removed off the event loop: removing
        an object store can mean megabytes of blobs, and the server has a
        socket to keep answering on.
        """
        index = await asyncio.to_thread(_temporary_index)
        throwaway: str | None = None
        try:
            throwaway = await asyncio.to_thread(_temporary_objects) if self._objects is None else None
            objects = throwaway or str(self._objects)
            variables = {"GIT_INDEX_FILE": index, "GIT_OBJECT_DIRECTORY": objects}
            own = await _own_paths(path)
            # Whichever store is written to, the repository's own stays readable
            if own is not None:
                variables["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = str(own.objects)

            await self._seed(path, Path(index), own, variables)
            await _run(path, ["add", "-A"], variables)
            yield GitStagedTree(path, variables, keeps_objects=self._objects is not None)
        finally:
            await asyncio.to_thread(_remove_staging, index, throwaway)

    @override
    async def list_refs(self, path: Path) -> list[GitRef]:
        """The branches and tags worth offering as a base, most recent first.

        Capped: a repository with hundreds of branches would fill a menu
        nobody can read, and whoever wants an older one can open the review
        against it.
        """
        listed = await _run(
            path,
            [
                "for-each-ref",
                f"--count={REF_LIMIT}",
                # `creatordate`, not `committerdate`: an annotated tag is a tag
                # object with a tagger and no committer, so committerdate comes
                # back empty and every such tag is dropped — from a project that
                # tags its releases properly, all of them
                "--sort=-creatordate",
                "--format=%(refname:short)%09%(creatordate:unix)",
                "refs/heads",
                "refs/tags",
            ],
        )
        refs = []
        for line in listed.splitlines():
            name, _, at = line.partition("\t")
            # A name may begin with a dash: `git check-ref-format` allows it and
            # a fetch can bring one in from a remote. Offered as a base it would
            # reach `git diff` as an option — `--output=` writes a file — so it
            # is not offered at all.
            if name and not name.startswith("-") and at.isdigit():
                # Git says seconds; the review says every time in milliseconds
                refs.append(GitRef(name=name, at=int(at) * MILLISECONDS_PER_SECOND))
        return refs

    @override
    async def changed_paths(self, path: Path) -> list[str]:
        """Every path where the working tree differs from HEAD.

        Asked twice a second for as long as a review is open, so it takes no
        lock: by default `git status` refreshes the index under `index.lock`,
        and the agent's own `git add` or `git commit` would then fail on it.
        Every file of an untracked directory is named, not the directory, so a
        file added inside one is a path of its own; renames are two paths.
        `-z` keeps every name as it is, unquoted.
        """
        listed = await _run(
            path,
            ["status", "--porcelain", "-z", "--untracked-files=all", "--no-renames"],
            {"GIT_OPTIONAL_LOCKS": "0"},
        )
        # Each entry is two status letters, a space, then the path
        return [entry[PORCELAIN_PATH_START:] for entry in listed.split("\0") if entry]

    @override
    async def is_tracked(self, root: Path, relative_path: str) -> bool:
        """Whether the repository tracks the file at this path."""
        try:
            run = await _execute(root, ["ls-files", "--error-unmatch", "--", relative_path], variables=None)
        except GitError:
            return False
        return run.exit_code == 0

    @override
    async def top_level(self, path: Path) -> Path | None:
        """The root of the repository containing ``path``.

        Git reports diff paths relative to this, not to whatever directory
        the command was run from, so anything resolving those paths has to
        start here or it looks for `sub/a.py` inside `sub/`.
        """
        try:
            found = await _run(path, ["rev-parse", "--show-toplevel"])
        except GitError:
            return None
        return Path(found.strip()) if found.strip() else None

    async def _seed(self, path: Path, index: Path, own: OwnPaths | None, variables: dict[str, str]) -> None:
        """Start a staging's index from the repository's own, from HEAD when it has none, or from nothing.

        Nothing is no file at all: git reads an empty file as a broken index,
        and a missing one as an empty index.
        """
        if own is not None and await asyncio.to_thread(own.index.is_file):
            # With its times kept: git reads a file saved in the same second as
            # the index was written as maybe changed only by comparing the two,
            # and a copy dated now would have it trust a stale stat instead
            await asyncio.to_thread(shutil.copy2, own.index, index)
        elif await _has_commits(path):
            await _run(path, ["read-tree", HEAD], variables)
        else:
            await asyncio.to_thread(index.unlink)


async def _own_paths(path: Path) -> OwnPaths | None:
    """Where the repository keeps its own objects and index, asked in one call, if git will say."""
    try:
        found = await _run(
            path, ["rev-parse", "--path-format=absolute", "--git-path", OBJECTS_NAME, "--git-path", INDEX_NAME]
        )
    except GitError:
        return None
    objects, _, index = found.strip().partition("\n")
    return OwnPaths(objects=Path(objects), index=Path(index)) if objects and index else None


async def _has_commits(path: Path) -> bool:
    """Whether there is a HEAD to start the index from: a fresh repository has none."""
    try:
        run = await _execute(path, ["rev-parse", "--verify", "--quiet", HEAD], variables=None)
    except GitError:
        return False
    return run.exit_code == 0


async def _run(path: Path, arguments: list[str], variables: dict[str, str] | None = None) -> str:
    """What a git command printed.

    Raises:
        GitError: if it could not run, ran out of time, or failed.
    """
    run = await _execute(path, arguments, variables)
    if run.exit_code != 0:
        log.warning("git_command_failed", command=arguments[0], exit_code=run.exit_code)
        msg = f"git command failed: {run.errors.strip()}"
        raise GitError(msg)
    return run.output


async def _execute(path: Path, arguments: list[str], variables: dict[str, str] | None) -> GitRun:
    """Run git and say how it went, leaving no process behind whatever happens.

    `variables` are what the command sets in git's environment; the rest is
    inherited, but for what would point git elsewhere or reshape its diff.
    Output is decoded as UTF-8 with anything else replaced: one file in
    another encoding costs its own odd characters, not the review.

    Raises:
        GitError: if git could not be started or ran out of time.
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "git",
            *GIT_SETTINGS,
            *arguments,
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_git_environment(variables or {}),
        )
    except (FileNotFoundError, NotADirectoryError) as failure:
        msg = f"git operation failed: {failure}"
        raise GitError(msg) from failure

    try:
        output, errors = await asyncio.wait_for(process.communicate(), timeout=GIT_TIMEOUT)
    except TimeoutError:
        await _stop(process)
        msg = f"git command timed out after {GIT_TIMEOUT}s: git {arguments[0]}"
        raise GitError(msg) from None
    except BaseException:
        # Cancelled while git was working: the process goes with the task
        await _stop(process)
        raise

    return GitRun(
        exit_code=await process.wait(),
        output=output.decode(errors="replace"),
        errors=errors.decode(errors="replace"),
    )


def _git_environment(variables: dict[str, str]) -> dict[str, str]:
    """The environment a git command runs in: the inherited one without what is foreign to it, and what it sets."""
    inherited = {name: value for name, value in os.environ.items() if name not in FOREIGN_GIT_VARIABLES}
    return inherited | EVERY_COMMAND_SETS | variables


async def _stop(process: asyncio.subprocess.Process) -> None:
    """End a git process and wait for it, so it is not left as a zombie."""
    with contextlib.suppress(ProcessLookupError):
        process.kill()
    await process.wait()


def _temporary_index() -> str:
    """A file of its own for one staging to use as git's index."""
    handle, index = tempfile.mkstemp(suffix=INDEX_SUFFIX)
    os.close(handle)
    return index


def _temporary_objects() -> str:
    """A directory of its own for one staging to write objects nobody keeps."""
    return tempfile.mkdtemp(suffix=OBJECTS_SUFFIX)


def _remove_staging(index: str, throwaway: str | None) -> None:
    Path(index).unlink(missing_ok=True)
    if throwaway is not None:
        shutil.rmtree(throwaway, ignore_errors=True)

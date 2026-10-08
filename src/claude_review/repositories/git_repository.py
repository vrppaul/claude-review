import asyncio
import contextlib
import os
import shutil
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import structlog
from pydantic import BaseModel

from claude_review.domain.exceptions import GitError
from claude_review.domain.models import GitRef

log = structlog.get_logger()


GIT_TIMEOUT = 30.0
REF_LIMIT = 50
# Where the path starts in an entry of `git status --porcelain`
PORCELAIN_PATH_START = 3

# Settings every command runs with, whatever the reader's configuration says:
# a path outside plain ASCII keeps git's own quoting, which the parser decodes
GIT_SETTINGS = ["-c", "core.quotePath=true"]

# How a diff is written, whatever the reader's configuration says. The parser
# reads one format: a diff tool of the reader's own, colours, other prefixes
# or paths relative to a subdirectory must not stand in for it.
DIFF_STAGED = [
    "diff",
    "--cached",
    "--no-ext-diff",
    "--no-color",
    "--no-relative",
    "--src-prefix=a/",
    "--dst-prefix=b/",
]

# Ends the options, so a revision that follows can never be read as one
END_OF_OPTIONS = "--end-of-options"

# What the temporary pieces of one staging are called, to be told apart in /tmp
INDEX_SUFFIX = ".git-index"
OBJECTS_SUFFIX = ".git-objects"


class GitRun(BaseModel):
    """What one git command said, and how it ended."""

    exit_code: int
    output: str
    errors: str


class GitRepository:
    """Git repository implementation using the git CLI.

    Uses a temporary index to diff ALL changes (tracked + untracked)
    without modifying the user's actual staging area.
    """

    def __init__(self, objects: Path | None = None) -> None:
        """Take the object store that staging writes to.

        Staging writes a blob for every untracked file, and those do not
        belong in the repository under review — it would otherwise gain one
        per file, and a tree with a large untracked build directory left
        megabytes behind. None throws them away when the call ends, which is
        right for a diff read once. A directory given here keeps them for as
        long as it lasts, which is what lets a snapshot be read back later:
        the review owns that directory and takes it with it.
        """
        self._objects = objects

    async def get_raw_diff(
        self,
        path: Path,
        base: str | None = None,
        *,
        ignore_whitespace: bool = False,
    ) -> str:
        """Return unified diff of all changes including untracked files.

        Creates a temporary git index, stages everything there, and diffs
        against a base ref. When base is None, diffs against HEAD (uncommitted
        changes only). When base is provided, diffs from that commit — or from
        a tree a round was snapshotted as — to the current working tree. The
        real index is untouched.

        With ignore_whitespace, git leaves out changes that only alter
        whitespace — a reindented block stops hiding the one line that
        actually changed inside it.
        """
        arguments = [*DIFF_STAGED, *(["-w"] if ignore_whitespace else [])]
        if base is not None:
            arguments += [END_OF_OPTIONS, base]
        async with self._everything_staged(path) as env:
            return await self._run(path, arguments, env=env)

    async def snapshot(self, path: Path) -> str:
        """Write the working tree as it stands and return the tree's id.

        This is how a round leaves a mark. The work under review is
        uncommitted, so between two rounds there may be no commit at all —
        without a tree written here, "what changed since round 2" has nothing
        to be compared against.

        Raises:
            GitError: if this repository throws its objects away, which would
                leave a tree id naming something nobody can read.
        """
        if self._objects is None:
            msg = "a snapshot needs an object store that outlives the call that took it"
            raise GitError(msg)

        async with self._everything_staged(path) as env:
            return (await self._run(path, ["write-tree"], env=env)).strip()

    async def changed_since(self, path: Path, bases: list[str]) -> dict[str, list[str]]:
        """Which paths differ between each of these bases and the working tree.

        The comparison a diff makes, asked for names alone: what a round
        changed is a list of files, and reading the hunks to find it out
        costs the whole diff. One staging serves every base, because building
        the index is the expensive part and it does not depend on what is
        being compared against. `-z` because git otherwise quotes and escapes
        any path outside plain ASCII, and these are matched against the paths
        already on screen.
        """
        changed: dict[str, list[str]] = {}
        async with self._everything_staged(path) as env:
            for base in bases:
                try:
                    listed = await self._run(path, [*DIFF_STAGED, "--name-only", "-z", END_OF_OPTIONS, base], env=env)
                except GitError:
                    # One base git will not read — a repository with no HEAD,
                    # a tree that has been pruned — is one base missing from
                    # the answer, not the end of the question
                    log.warning("changed_since_refused", base=base)
                    continue
                changed[base] = [name for name in listed.split("\0") if name]
        return changed

    async def list_refs(self, path: Path) -> list[GitRef]:
        """The branches and tags worth offering as a base, most recent first.

        Capped: a repository with hundreds of branches would fill a menu
        nobody can read, and whoever wants an older one can open the review
        against it.
        """
        listed = await self._run(
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
                refs.append(GitRef(name=name, at=int(at)))
        return refs

    @contextlib.asynccontextmanager
    async def _everything_staged(self, path: Path) -> AsyncGenerator[dict[str, str]]:
        """Stage the whole working tree into an index of this call's own.

        Yields the environment the git commands have to run under to see it:
        which index they read, and where what they write goes. The temporary
        files are made and removed off the event loop: removing an object
        store can mean megabytes of blobs, and the server has a socket to
        keep answering on.
        """
        index = await asyncio.to_thread(_temporary_index)
        throwaway = await asyncio.to_thread(_temporary_objects) if self._objects is None else None
        objects = throwaway or str(self._objects)
        env = {**os.environ, "GIT_INDEX_FILE": index, "GIT_OBJECT_DIRECTORY": objects}

        try:
            # Whichever store is written to, the repository's own stays readable
            real_objects = await self._object_directory(path)
            if real_objects is not None:
                env["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = real_objects

            if await self._has_commits(path):
                await self._run(path, ["read-tree", "HEAD"], env=env)

            await self._run(path, ["add", "-A"], env=env)
            yield env
        finally:
            await asyncio.to_thread(_remove_staging, index, throwaway)

    async def _object_directory(self, path: Path) -> str | None:
        """Absolute path of the repository's object store, if git will say."""
        try:
            found = await self._run(path, ["rev-parse", "--path-format=absolute", "--git-path", "objects"])
        except GitError:
            return None
        return found.strip() or None

    async def changed_paths(self, path: Path) -> list[str]:
        """Every path where the working tree differs from HEAD.

        Asked twice a second for as long as a review is open, so it takes no
        lock: by default `git status` refreshes the index under `index.lock`,
        and the agent's own `git add` or `git commit` would then fail on it.
        Every file of an untracked directory is named, not the directory, so a
        file added inside one is a path of its own; renames are two paths.
        `-z` keeps every name as it is, unquoted.
        """
        listed = await self._run(
            path,
            ["status", "--porcelain", "-z", "--untracked-files=all", "--no-renames"],
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
        # Each entry is two status letters, a space, then the path
        return [entry[PORCELAIN_PATH_START:] for entry in listed.split("\0") if entry]

    async def is_tracked(self, root: Path, relative_path: str) -> bool:
        """Whether the repository tracks the file at this path."""
        try:
            run = await self._execute(root, ["ls-files", "--error-unmatch", "--", relative_path])
        except GitError:
            return False
        return run.exit_code == 0

    async def top_level(self, path: Path) -> Path | None:
        """The root of the repository containing ``path``.

        Git reports diff paths relative to this, not to whatever directory
        the command was run from, so anything resolving those paths has to
        start here or it looks for `sub/a.py` inside `sub/`.
        """
        try:
            found = await self._run(path, ["rev-parse", "--show-toplevel"])
        except GitError:
            return None
        return Path(found.strip()) if found.strip() else None

    async def _has_commits(self, path: Path) -> bool:
        """Whether there is a HEAD to start the index from: a fresh repository has none."""
        try:
            run = await self._execute(path, ["rev-parse", "--verify", "--quiet", "HEAD"])
        except GitError:
            return False
        return run.exit_code == 0

    async def _run(self, path: Path, arguments: list[str], env: dict[str, str] | None = None) -> str:
        """What a git command printed.

        Raises:
            GitError: if it could not run, ran out of time, or failed.
        """
        run = await self._execute(path, arguments, env)
        if run.exit_code != 0:
            log.warning("git_command_failed", command=arguments[0], exit_code=run.exit_code)
            msg = f"git command failed: {run.errors.strip()}"
            raise GitError(msg)
        return run.output

    async def _execute(self, path: Path, arguments: list[str], env: dict[str, str] | None = None) -> GitRun:
        """Run git and say how it went, leaving no process behind whatever happens.

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
                env=env,
            )
        except (FileNotFoundError, NotADirectoryError) as e:
            msg = f"git operation failed: {e}"
            raise GitError(msg) from e

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
    with contextlib.suppress(FileNotFoundError):
        os.unlink(index)
    if throwaway is not None:
        shutil.rmtree(throwaway, ignore_errors=True)

import asyncio
import contextlib
import os
import shutil
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import structlog

from claude_review.domain.exceptions import GitError
from claude_review.domain.models import GitRef

log = structlog.get_logger()


GIT_TIMEOUT = 30.0
REF_LIMIT = 50


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
        async with self._everything_staged(path) as env:
            diff_cmd = ["git", "diff", "--cached"]
            if base is not None:
                diff_cmd = ["git", "diff", base, "--cached"]
            if ignore_whitespace:
                diff_cmd.append("-w")
            return await self._run(path, diff_cmd, env=env)

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
            return (await self._run(path, ["git", "write-tree"], env=env)).strip()

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
                    listed = await self._run(path, ["git", "diff", base, "--cached", "--name-only", "-z"], env=env)
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
                "git",
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
    async def _everything_staged(self, path: Path) -> AsyncIterator[dict[str, str]]:
        """Stage the whole working tree into an index of this call's own.

        Yields the environment the git commands have to run under to see it:
        which index they read, and where what they write goes.
        """
        fd, tmp_index = tempfile.mkstemp(suffix=".git-index")
        os.close(fd)
        throwaway = tempfile.mkdtemp(suffix=".git-objects") if self._objects is None else None
        objects = throwaway or str(self._objects)
        env = {**os.environ, "GIT_INDEX_FILE": tmp_index, "GIT_OBJECT_DIRECTORY": objects}

        # Whichever store is written to, the repository's own stays readable
        real_objects = await self._object_directory(path)
        if real_objects is not None:
            env["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = real_objects

        try:
            if await self._has_commits(path):
                await self._run(path, ["git", "read-tree", "HEAD"], env=env)

            await self._run(path, ["git", "add", "-A"], env=env)
            yield env
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp_index)
            if throwaway is not None:
                shutil.rmtree(throwaway, ignore_errors=True)

    async def _object_directory(self, path: Path) -> str | None:
        """Absolute path of the repository's object store, if git will say."""
        try:
            found = await self._run(path, ["git", "rev-parse", "--path-format=absolute", "--git-path", "objects"])
        except GitError:
            return None
        return found.strip() or None

    async def status(self, path: Path) -> str:
        """What git says has changed, one line per path.

        `--porcelain` is the stable form: it does not change with the user's
        config or git's version, which matters because this is compared
        against itself twice a second.
        """
        return await self._run(path, ["git", "status", "--porcelain"])

    async def top_level(self, path: Path) -> Path | None:
        """The root of the repository containing ``path``.

        Git reports diff paths relative to this, not to whatever directory
        the command was run from, so anything resolving those paths has to
        start here or it looks for `sub/a.py` inside `sub/`.
        """
        try:
            found = await self._run(path, ["git", "rev-parse", "--show-toplevel"])
        except GitError:
            return None
        return Path(found.strip()) if found.strip() else None

    async def _has_commits(self, path: Path) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "rev-parse",
                "HEAD",
                cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=GIT_TIMEOUT)
            return proc.returncode == 0
        except (FileNotFoundError, NotADirectoryError):  # fmt: skip
            return False
        except TimeoutError:
            proc.kill()
            return False

    async def _run(self, path: Path, cmd: list[str], env: dict[str, str] | None = None) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except (FileNotFoundError, NotADirectoryError) as e:
            msg = f"git operation failed: {e}"
            raise GitError(msg) from e

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=GIT_TIMEOUT)
        except TimeoutError:
            proc.kill()
            msg = f"git command timed out after {GIT_TIMEOUT}s: {' '.join(cmd[:2])}"
            raise GitError(msg) from None

        if proc.returncode != 0:
            msg = f"git command failed: {stderr.decode().strip()}"
            log.warning("git_command_failed", cmd=cmd[:2], returncode=proc.returncode)
            raise GitError(msg)

        return stdout.decode()

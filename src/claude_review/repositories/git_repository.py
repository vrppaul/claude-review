import asyncio
import contextlib
import os
import shutil
import tempfile
from pathlib import Path

import structlog

from claude_review.domain.exceptions import GitError

log = structlog.get_logger()


GIT_TIMEOUT = 30.0


class GitRepository:
    """Git repository implementation using the git CLI.

    Uses a temporary index to diff ALL changes (tracked + untracked)
    without modifying the user's actual staging area.
    """

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
        changes only). When base is provided, diffs from that commit to the
        current working tree. The real index is untouched.

        With ignore_whitespace, git leaves out changes that only alter
        whitespace — a reindented block stops hiding the one line that
        actually changed inside it.
        """
        fd, tmp_index = tempfile.mkstemp(suffix=".git-index")
        os.close(fd)
        tmp_objects = tempfile.mkdtemp(suffix=".git-objects")
        env = {**os.environ, "GIT_INDEX_FILE": tmp_index, "GIT_OBJECT_DIRECTORY": tmp_objects}

        # Staging writes a blob for every untracked file. Sending those to a
        # directory that is thrown away afterwards keeps them out of the
        # repository, which would otherwise gain one per file — a review of a
        # tree with a large untracked build directory left megabytes behind.
        # The real object store is still readable as an alternate.
        real_objects = await self._object_directory(path)
        if real_objects is not None:
            env["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = real_objects

        try:
            if await self._has_commits(path):
                await self._run(path, ["git", "read-tree", "HEAD"], env=env)

            await self._run(path, ["git", "add", "-A"], env=env)

            diff_cmd = ["git", "diff", "--cached"]
            if base is not None:
                diff_cmd = ["git", "diff", base, "--cached"]
            if ignore_whitespace:
                diff_cmd.append("-w")
            return await self._run(path, diff_cmd, env=env)
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp_index)
            shutil.rmtree(tmp_objects, ignore_errors=True)

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

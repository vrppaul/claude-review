import asyncio
import contextlib
import os
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

    async def get_raw_diff(self, path: Path, base: str | None = None) -> str:
        """Return unified diff of all changes including untracked files.

        Creates a temporary git index, stages everything there, and diffs
        against a base ref. When base is None, diffs against HEAD (uncommitted
        changes only). When base is provided, diffs from that commit to the
        current working tree. The real index is untouched.
        """
        fd, tmp_index = tempfile.mkstemp(suffix=".git-index")
        os.close(fd)
        env = {**os.environ, "GIT_INDEX_FILE": tmp_index}

        try:
            if await self._has_commits(path):
                await self._run(path, ["git", "read-tree", "HEAD"], env=env)

            await self._run(path, ["git", "add", "-A"], env=env)

            diff_cmd = ["git", "diff", "--cached"]
            if base is not None:
                diff_cmd = ["git", "diff", base, "--cached"]
            return await self._run(path, diff_cmd, env=env)
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp_index)

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

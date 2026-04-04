"""Git repository for accessing diff data."""

import asyncio
import contextlib
import os
import tempfile
from pathlib import Path

from claude_review.domain.exceptions import GitError


class GitRepository:
    """Git repository implementation using the git CLI.

    Uses a temporary index to diff ALL changes (tracked + untracked)
    without modifying the user's actual staging area.
    """

    async def get_raw_diff(self, path: Path) -> str:
        """Return unified diff of all changes including untracked files.

        Creates a temporary git index, stages everything there, and diffs
        against HEAD. For repos with no commits, git diff --cached implicitly
        diffs against the empty tree. The real index is untouched.
        """
        fd, tmp_index = tempfile.mkstemp(suffix=".git-index")
        os.close(fd)
        env = {**os.environ, "GIT_INDEX_FILE": tmp_index}

        try:
            if await self._has_commits(path):
                await self._run(path, ["git", "read-tree", "HEAD"], env=env)

            await self._run(path, ["git", "add", "-A"], env=env)
            return await self._run(path, ["git", "diff", "--cached"], env=env)
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp_index)

    async def _has_commits(self, path: Path) -> bool:
        """Check if the repo has at least one commit."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "rev-parse",
                "HEAD",
                cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        except FileNotFoundError, NotADirectoryError:
            return False

    async def _run(self, path: Path, cmd: list[str], env: dict | None = None) -> str:
        """Run a git command and return stdout."""
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

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            msg = f"git command failed: {stderr.decode().strip()}"
            raise GitError(msg)

        return stdout.decode()

"""Custom hatch build hook that builds the frontend before packaging."""

import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class FrontendBuildHook(BuildHookInterface):
    PLUGIN_NAME = "frontend-build"

    def initialize(self, version: str, build_data: dict) -> None:
        frontend_dir = Path(self.root) / "frontend"
        static_dir = Path(self.root) / "src" / "claude_review" / "static" / "dist"

        if not frontend_dir.exists():
            return

        # Skip if pnpm is not available (e.g. lint-only CI jobs)
        if not shutil.which("pnpm"):
            if static_dir.exists():
                return  # pre-built assets exist, proceed without building
            msg = "pnpm is required to build the frontend"
            raise RuntimeError(msg)

        subprocess.run(["pnpm", "install", "--frozen-lockfile"], cwd=frontend_dir, check=True)
        subprocess.run(["pnpm", "build"], cwd=frontend_dir, check=True)

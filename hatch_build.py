"""Custom hatch build hook that builds the frontend before packaging."""

import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class FrontendBuildHook(BuildHookInterface):
    PLUGIN_NAME = "frontend-build"

    def initialize(self, version: str, build_data: dict) -> None:
        frontend_dir = Path(self.root) / "frontend"

        if not frontend_dir.exists():
            return

        if not shutil.which("pnpm"):
            return

        subprocess.run(["pnpm", "install", "--frozen-lockfile"], cwd=frontend_dir, check=True)
        subprocess.run(["pnpm", "build"], cwd=frontend_dir, check=True)

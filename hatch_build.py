"""Custom hatch build hook that builds the frontend before packaging.

Build contexts this must handle:
- Git checkout with pnpm (dev machine, release CI): rebuild the frontend.
- Git checkout without pnpm: fail loudly for distribution builds — a silent skip
  would ship a wheel with no UI. Editable installs (uv sync, CI lint/test jobs)
  only warn, since they don't produce a distributable artifact.
- Sdist (no frontend/ directory): use the prebuilt assets shipped in the sdist,
  so building from sdist never requires Node/pnpm.
"""

import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

PNPM_MISSING = (
    "pnpm is required to build the claude-review frontend from source. "
    "Install pnpm (https://pnpm.io) or install the prebuilt package from PyPI: "
    "uv tool install claude-review"
)


class FrontendBuildHook(BuildHookInterface):
    PLUGIN_NAME = "frontend-build"

    def initialize(self, version: str, build_data: dict) -> None:
        root = Path(self.root)
        frontend_dir = root / "frontend"
        prebuilt_index = root / "src" / "claude_review" / "static" / "dist" / "index.html"

        if not frontend_dir.exists():
            if not prebuilt_index.exists():
                raise RuntimeError(
                    "Prebuilt frontend assets are missing (src/claude_review/static/dist/); "
                    "the package would serve no UI. This sdist is broken — install from PyPI "
                    "instead: uv tool install claude-review"
                )
            return

        if not shutil.which("pnpm"):
            if version == "editable":
                # Keep the assets dir present so packaging's force-include doesn't
                # fail; the server serves no UI until `pnpm build` runs.
                prebuilt_index.parent.mkdir(parents=True, exist_ok=True)
                self.app.display_warning(f"Skipping frontend build: {PNPM_MISSING}")
                return
            raise RuntimeError(PNPM_MISSING)

        subprocess.run(["pnpm", "install", "--frozen-lockfile"], cwd=frontend_dir, check=True)
        subprocess.run(["pnpm", "build"], cwd=frontend_dir, check=True)

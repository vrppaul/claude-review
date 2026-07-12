"""Verify built distribution artifacts are self-contained and version-consistent.

Run after `uv build`. Guards the invariants that make claude-review installable
on machines without Node/pnpm:
- the wheel ships the built frontend (static/dist)
- the sdist ships prebuilt frontend assets and no frontend/ sources, so
  building a wheel from it needs no JS toolchain

Also enforces the release rule that pyproject.toml and the Claude Code plugin
manifest advertise the same version, and that no source maps bloat the
artifacts. Used by both ci.yml (build job) and release.yml (pre-publish).
"""

import json
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).parent.parent


def fail(message: str) -> NoReturn:
    print(f"FAIL: {message}")
    sys.exit(1)


def expected_version() -> str:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    version: str = pyproject["project"]["version"]
    plugin_manifest = json.loads((ROOT / "plugin" / ".claude-plugin" / "plugin.json").read_text())
    if plugin_manifest["version"] != version:
        fail(f"version mismatch: pyproject.toml has {version}, plugin.json has {plugin_manifest['version']}")
    return version


def find_artifact(pattern: str) -> Path:
    matches = list((ROOT / "dist").glob(pattern))
    if len(matches) != 1:
        fail(f"expected exactly one dist/{pattern}, found: {[m.name for m in matches]}")
    return matches[0]


def check_no_sourcemaps(name: str, files: list[str]) -> None:
    maps = [f for f in files if f.endswith(".map")]
    if maps:
        fail(f"{name} ships source maps ({maps}) — keep sourcemap: false in frontend/vite.config.ts")


def check_wheel(wheel: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        files = archive.namelist()
    if "claude_review/static/dist/index.html" not in files:
        fail(f"{wheel.name} is missing the UI entry point (static/dist/index.html)")
    assets = [f for f in files if f.startswith("claude_review/static/dist/assets/")]
    for extension in (".js", ".css"):
        if not any(f.endswith(extension) for f in assets):
            fail(f"{wheel.name} is missing built {extension} assets, got: {assets}")
    check_no_sourcemaps(wheel.name, files)


def check_sdist(sdist: Path, version: str) -> None:
    with tarfile.open(sdist) as archive:
        files = archive.getnames()
    prefix = f"claude_review-{version}"
    if f"{prefix}/src/claude_review/static/dist/index.html" not in files:
        fail(f"{sdist.name} is missing prebuilt UI assets — building a wheel from it would require pnpm")
    if f"{prefix}/hatch_build.py" not in files:
        fail(f"{sdist.name} is missing hatch_build.py — the build hook could not run")
    if any(f.startswith(f"{prefix}/frontend/") for f in files):
        fail(f"{sdist.name} ships frontend/ sources — building from sdist must not need pnpm")
    check_no_sourcemaps(sdist.name, files)


def main() -> None:
    version = expected_version()
    wheel = find_artifact(f"claude_review-{version}-*.whl")
    sdist = find_artifact(f"claude_review-{version}.tar.gz")
    check_wheel(wheel)
    check_sdist(sdist, version)
    print(f"OK: {wheel.name} and {sdist.name} are self-contained and version-consistent")


if __name__ == "__main__":
    main()

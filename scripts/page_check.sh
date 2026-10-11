#!/usr/bin/env bash
# Runs one of the page's pnpm scripts for a pre-commit hook:
#
#     bash scripts/page_check.sh lint
#
# A hook that cannot run must not pass for one that found nothing, so without
# pnpm it fails and says so. Where the page cannot be checked, the hook is left
# out on purpose by naming it in SKIP, as CI's lint job leaves out the page's
# checks that its own jobs run.
set -euo pipefail

if ! command -v pnpm >/dev/null; then
    echo "pnpm is not installed, so the page cannot be checked: install it, or name this hook in SKIP" >&2
    exit 1
fi
cd "$(dirname "$0")/../frontend"
exec pnpm "$@"

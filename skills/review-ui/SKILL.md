---
name: review-ui
description: Open a browser-based review UI to comment on current git changes or plan files
user-invocable: true
---

Open the claude-review diff viewer in the browser so the user can review code changes and leave inline comments.

Usage:
- `/review-ui` — review current git changes
- `/review-ui plan` — review the current plan file

## Steps

1. Check if `claude-review` is installed and up to date:
   ```bash
   claude-review --help 2>&1 | grep -q '\-\-files' && echo "up-to-date" || echo "needs-update"
   ```

2. If not installed or needs update, install/upgrade it:
   ```bash
   uv tool install --upgrade git+https://github.com/vrppaul/claude-review
   ```

3. Determine the mode:
   - If the argument is `plan`: find the current plan file path from your system prompt (look for the plan file path mentioned in the "Plan File Info" section). Run:
     ```bash
     claude-review --files <plan-file-path>
     ```
   - If no argument: run the default git diff review:
     ```bash
     claude-review
     ```

When it finishes, the user's review comments will be printed to stdout. Read them carefully and address each comment by making the requested changes.

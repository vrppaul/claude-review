---
name: review-ui
description: Open a browser-based review UI to comment on current git changes
---

Open the claude-review diff viewer in the browser so the user can review code changes and leave inline comments.

Accepts an optional argument:
- No argument: review current git changes (default)
- `plan`: review the current plan file

## Steps

1. Check if `claude-review` is installed:
   ```bash
   which claude-review
   ```

2. If not installed, install it:
   ```bash
   uv tool install git+https://github.com/vrppaul/claude-review
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

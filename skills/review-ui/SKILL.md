---
name: review-ui
description: Open a browser-based review UI to comment on current git changes
user-invocable: true
---

Open the claude-review diff viewer in the browser so the user can review code changes and leave inline comments.

## Steps

1. Check if `claude-review` is installed:
   ```bash
   which claude-review
   ```

2. If not installed, install it:
   ```bash
   uv tool install git+https://github.com/vrppaul/claude-review
   ```

3. Run claude-review and wait for it to complete:
   ```bash
   claude-review
   ```

When it finishes, the user's review comments will be printed to stdout. Read them carefully and address each comment by making the requested changes.

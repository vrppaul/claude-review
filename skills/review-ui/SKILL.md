---
name: review-ui
description: Open a browser-based review UI to comment on current git changes, plan files, or conversation transcripts
user-invocable: true
---

Open the claude-review diff viewer in the browser so the user can review code changes and leave inline comments.

Usage:
- `/review-ui` — review current git changes
- `/review-ui plan` — review the current plan file
- `/review-ui transcript` — review the current conversation as a transcript

## Steps

1. Install or upgrade `claude-review` to the latest version:
   ```bash
   uv tool install --upgrade git+https://github.com/vrppaul/claude-review
   ```

2. Determine the mode:
   - If the argument is `plan`: find the current plan file path from your system prompt (look for the plan file path mentioned in the "Plan File Info" section). Run:
     ```bash
     claude-review --files <plan-file-path>
     ```
   - If the argument is `transcript`: find the current conversation JSONL file. It lives at `~/.claude/projects/<project-dir-hash>/<session-id>.jsonl` — the session ID is in your system prompt. Run:
     ```bash
     claude-review --transcript <path-to-jsonl>
     ```
   - If no argument: run the default git diff review:
     ```bash
     claude-review
     ```

When it finishes, the user's review comments will be printed to stdout. Read them carefully and address each comment by making the requested changes.

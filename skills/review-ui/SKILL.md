---
name: review-ui
description: Open a browser-based review UI to comment on current git changes, with markdown preview
user-invocable: true
---

Open the claude-review diff viewer in the browser so the user can review code changes and leave inline comments. Markdown files and transcripts support Raw, Preview, and Side-by-side view modes.

Usage:
- `/review-ui` — review current git changes
- `/review-ui last 3 commits` — review changes from the last 3 commits
- `/review-ui since v0.5.0` — review changes since a tag
- `/review-ui plan` — review the current plan file
- `/review-ui transcript` — review the current conversation as a transcript

## Steps

1. Install or upgrade `claude-review` to the latest version:
   ```bash
   uv tool install --upgrade git+https://github.com/vrppaul/claude-review
   ```

2. Determine the mode:
   - If the argument is `plan`: run `claude-review files <plan-file-path>` (find the plan file path in the "Plan File Info" section of your system prompt).
   - If the argument is `transcript`: run `claude-review transcript <path-to-jsonl>` (find the JSONL at `~/.claude/projects/<project-dir-hash>/<session-id>.jsonl`).
   - Otherwise it's a diff review. Translate the argument to a `claude-review diff` command:
     - No argument → `claude-review diff`
     - `diff` → `claude-review diff`
     - `diff --base HEAD~3` → `claude-review diff --base HEAD~3`
     - `last 3 commits` → `claude-review diff --base HEAD~3`
     - `two last commits` → `claude-review diff --base HEAD~2`
     - `since v0.5.0` → `claude-review diff --base v0.5.0`
     - Any natural language describing a commit range → figure out the git ref and pass it as `--base`

When it finishes, the user's review comments will be printed to stdout. Read them carefully and address each comment by making the requested changes.

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
   uv tool install --upgrade claude-review
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

## Discussing a thread while the review is open (optional)

Skip this unless the user asks for it, or has asked a question in a thread
before. It changes nothing about the flow above; it adds a second half.

The review UI has an "Ask Claude" button on every comment. A question left
there waits for you to pick it up, and your answer appears in that thread
while the user keeps reading. To be available for that, run the review in the
background instead of waiting on it:

1. Start it in the background on a port you choose, and open the URL yourself:
   ```bash
   claude-review --port 8765 --no-open diff
   ```
   If the port is taken the command says so; pick another.

2. Loop until the review is sent:
   ```bash
   claude-review wait --port 8765 --seconds 25
   ```
   It prints one JSON object and exits:
   - `{"type": "question", "question": {...}}` — answer it, then wait again.
     The question carries `thread_id`, the file, the line range and `quote`,
     the lines it is about.
   - `{"type": "timeout"}` — nothing was asked; wait again.

3. Answer in the thread it belongs to:
   ```bash
   claude-review reply --port 8765 --thread <thread_id> "..."
   ```
   Answer from what you know about this change — why you wrote it that way,
   what you considered and rejected. That context is the reason to route the
   question to you rather than to a fresh session.

4. The review's comments arrive on the background command's output when the
   user sends it, as they normally would. That ends the loop.

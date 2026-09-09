---
name: review-ui
description: Open a browser-based review UI to comment on current git changes, with markdown preview
---

Open the claude-review diff viewer in the browser so the user can review code changes and leave inline comments. Markdown files and transcripts support Raw, Preview, and Side-by-side view modes.

Usage:
- No argument: review current git changes
- `last 3 commits`, `since v0.5.0`, `diff --base HEAD~3`: review changes since a specific point
- `plan`: review the current plan file
- `transcript`: review the current conversation as a transcript

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

## Discussing a thread, and reviewing in rounds (optional)

Skip this unless the user asks for it, or has asked a question in a thread
before. It changes nothing about the flow above; it adds a second half.

Every thread in the review UI has an "Ask now" button, and the composer
offers it beside "Add to review". A question left there waits for you to
pick it up, and your answer appears in that thread while the user keeps
reading. Once you are waiting, the review also offers to send a **round**
rather than to end: the user sends what they have written, you answer and
make the changes, the diff is taken again, and the review carries on.

Two rules while the review is open. **Answer questions as they arrive** — a
thread that goes quiet for ten minutes reads as a hang, and the reader is
sitting in front of it. **Leave the changes for the round**: work through
what the review asks when a round arrives, not the moment a question hints
at it.

To be available for that, run the review in the background instead of
waiting on it:

1. Start it in the background on a port you choose, and open the URL yourself:
   ```bash
   claude-review --port 8765 --no-open diff
   ```
   If the port is taken the command says so; pick another. (Without `--port`
   the review picks one from the repository and the base ref, so reopening
   the same review comes back to the same address — and to the draft left
   in it.)

2. Loop until the review is over:
   ```bash
   claude-review wait --port 8765 --seconds 25
   ```
   It prints one JSON object and exits:
   - `{"type": "question", "question": {...}}` — answer it, then wait again.
     The question carries `thread_id` and `question_id`, the file, the line
     range, `quote` — the lines it is about — and `history`, everything
     already said in that thread, starting with the comment that opened it.
   - `{"type": "round", "round": {"number": 1, "markdown": "..."}}` — the
     user has sent a round. Address it as you would a finished review, then
     retake the diff (step 4) and keep waiting.
   - `{"type": "timeout"}` — nothing was asked; wait again.
   - `{"type": "closed"}` — the review is over. Stop.

3. Answer in the thread it belongs to, naming the question:
   ```bash
   claude-review reply --port 8765 --thread <thread_id> --question <question_id> "..."
   ```
   A thread can have more than one question waiting at once, which is why the
   answer names one: without it the answer is filed under whatever was asked
   last. Answer from what you know about this change — why you wrote it that
   way, what you considered and rejected. That context is the reason to route
   the question to you rather than to a fresh session.

4. After making the changes a round asked for, show them:
   ```bash
   claude-review round --port 8765
   ```
   The open review reloads the diff and moves its threads onto it: one whose
   lines survived follows them, one whose lines are gone is marked outdated
   and keeps a copy of what it was written against.

5. A review the user ends prints its last round on the background command's
   output, as it normally would. That ends the loop.

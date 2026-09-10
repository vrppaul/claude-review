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

## Talking through the review: threads, the panel, and rounds (optional)

Skip this unless the user asks for it, or has asked a question in a thread
before. It changes nothing about the flow above; it adds a second half.

Every thread in the review UI has an "Ask now" button, and the composer
offers it beside "Add to review". A question left there waits for you to
pick it up, and your answer appears in that thread while the user keeps
reading. The **agent panel** on the right is the same conversation for
everything a thread is not about — the plan, the tests, a file nobody
commented on — and what is typed there goes at once. Once you are waiting,
the review also offers to send a **round** rather than to end: the user
sends what they have written, you answer and make the changes, the diff is
taken again, and the review carries on.

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
   - `{"type": "message", "message": {"message_id": "panel-1", "text": "...",
     "threads": [...]}}` — the user has said something in the agent panel,
     which is about the review rather than about one line: the plan, the
     tests, a file nobody commented on. Answer it with `say` (step 4). Any
     threads it points at come with it, in the same shape as a question.
   - `{"type": "round", "round": {"number": 1, "markdown": "..."}}` — the
     user has sent a round. Address it as you would a finished review, then
     retake the diff (step 7) and keep waiting.
   - `{"type": "cancel", "cancel": {"message_id": "panel-1"}}` — the user has
     taken a message back. Drop what you were doing for it if you still can,
     and say nothing about it unless it is already half done.
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

4. Answer a panel message, naming the message:
   ```bash
   claude-review say --port 8765 --message <message_id> "..."
   ```
   The panel is one conversation, so the answer lands under the message it
   names. Optionally, say what only you can know about yourself — the panel
   shows it beside the review's own weight, with the time it was said:
   ```bash
   claude-review status --port 8765 --model opus-5 --context "53% of 1M"
   ```
   Report it when it changes, not on every turn. Say nothing and the panel
   shows nothing, which is better than a number that is a guess.

5. Point at a line, when what you have to say belongs on the code:
   ```bash
   claude-review point --port 8765 --file src/x.py --lines 118-130 \
     --severity question "I kept the old name here: renaming it broke two callers."
   ```
   Use it for what a paragraph in the panel would bury — where you did
   something other than what was asked, and why. It becomes an ordinary
   thread the reader answers, settles or removes, drawn as yours rather than
   as one of their marks, and it does not count as their unsent work.

6. Say what you are doing, while you are doing it:
   ```bash
   claude-review progress --port 8765 --message <message_id> \
     --file src/a.py --file src/b.py "rewriting the answer handler"
   ```
   Waiting says only that something is happening; this says what. Send it
   again to change it — it replaces what was showing rather than adding to
   it — and it goes away on its own when you answer. The files become chips
   the reader can jump by.

   Two more, for what a paragraph cannot do:
   ```bash
   claude-review say --port 8765 --file src/a.py "Renamed it here."
   claude-review show --port 8765 --file src/a.py
   ```
   `say --file` offers a jump the reader takes when they want it. `show`
   takes them there and marks the file for a moment — it moves somebody
   else's screen, so send it only when they asked to be shown something.

7. After making the changes a round asked for, show them:
   ```bash
   claude-review round --port 8765
   ```
   The open review reloads the diff and moves its threads onto it: one whose
   lines survived follows them, one whose lines are gone is marked outdated
   and keeps a copy of what it was written against.

8. A review the user ends prints its last round on the background command's
   output, as it normally would. That ends the loop.

While you work, the review says when the working tree has moved on and
offers the user a "Retake" of its own. It never swaps the diff by itself, so
nothing you change under a half-written comment throws it away.

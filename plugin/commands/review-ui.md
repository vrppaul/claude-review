---
name: review-ui
description: Open a review in the browser and stay attached to it — the user comments on a diff, files or a transcript, asks about any of it while they read, and sends rounds you answer without the review ending
---

Open the claude-review viewer so the user can read a change and mark it up.

It is a conversation, not a form. Every thread can be asked about while they
are still reading, the panel on the right takes what no single line covers,
and a round sends what they have written **without ending the review** — you
answer, make the changes, take the diff again, and they carry on from where
they were. None of that works unless something is there to answer, so the
review runs in the background and you stay in its loop.

Waiting on it in the foreground is the other shape, and it is right only
when there is nothing to talk about — it is at the end of this file. Do not
start there: a review nobody is attached to shows the user an "Ask now"
button on every thread and a panel that says, when they finally click,
that nobody is listening.

Usage:
- No argument: review current git changes
- `last 3 commits`, `since v0.5.0`, `diff --base HEAD~3`: review changes since a specific point
- `plan`: review the current plan file
- `transcript`: review the current conversation as a transcript

## Three rules while a review is open

**Answer questions as they arrive.** A thread that goes quiet for ten
minutes reads as a hang, and the reader is sitting in front of it.

**Leave the changes for the round.** Work through what the review asks when
a round arrives, not the moment a question hints at it.

**Say what you are doing while you do it** (step 8). Everything you do to
their code, the reader should be able to watch happening. A silent agent and
a hung one look the same from a browser, and the difference matters to
somebody who is waiting.

## Steps

1. Install or upgrade `claude-review` to the latest version:
   ```bash
   uv tool install --upgrade claude-review
   ```

2. Work out what is being reviewed:
   - `plan` → `claude-review files <plan-file-path>` (the path is in the
     "Plan File Info" section of your system prompt).
   - `transcript` → `claude-review transcript <path-to-jsonl>` (the JSONL is
     at `~/.claude/projects/<project-dir-hash>/<session-id>.jsonl`).
   - Anything else is a diff review. Translate the argument into a `--base`:
     - No argument, or `diff` → `claude-review diff`
     - `last 3 commits` → `claude-review diff --base HEAD~3`
     - `two last commits` → `claude-review diff --base HEAD~2`
     - `since v0.5.0` → `claude-review diff --base v0.5.0`
     - Any natural language describing a commit range → work out the git ref
       and pass it as `--base`

   The base is a starting point, not a commitment: the header lets the
   reader read the same working tree against a branch, a tag or an earlier
   round of this review.

3. Start it in the background. It opens in their browser by itself:
   ```bash
   setsid nohup claude-review --port 8765 diff > /tmp/review.log 2>&1 &
   ```
   Detached, rather than a bare `&`: started in the shell's own session, the
   review dies with that shell, and the next command you run takes the review
   down with it. `setsid` is the one that holds; where there is none — macOS
   ships no `setsid` — `nohup … &` on its own is the fallback.

   The address is printed to that log whether or not a window opened. Read it
   and give it to them anyway: over ssh or in a container there is nothing to
   open, and a tab closed by accident needs the way back. Pass `--no-open`
   only when you know a window would be wrong.

   If the port is taken the command says so; pick another. (Without `--port`
   the review picks one from the repository and the base ref, so reopening
   the same review comes back to the same address — and to the draft left
   in it.)

4. Catch up, if this review was already under way when you arrived:
   ```bash
   claude-review context --port 8765
   ```
   `wait` hands over what happens next, never what already happened — so an
   agent that restarted mid-review knows nothing until somebody says
   something. This prints the round, a line per thread and the panel in
   short. It is an index on purpose: `claude-review context --thread
   comment-4` gets that one thread in full, with its lines and every turn.
   `--json` is the same thing for a program to read rather than a person —
   worth it when you mean to count or filter rather than to catch up.

5. Stay in the loop until the review is over:
   ```bash
   claude-review wait --port 8765 --seconds 25
   ```
   It prints one JSON object and exits. Run it in a loop, in the background,
   so an event reaches you rather than you going back to look: a single call
   per turn also works, but the review is unattended between them, and that
   is the silence the first rule is about.
   - `{"type": "question", "question": {...}}` — answer it (step 6), then
     wait again. The question carries `thread_id` and `question_id`, the
     file, the line range, `quote` — the lines it is about — and `history`,
     everything already said in that thread, starting with the comment that
     opened it.
   - `{"type": "message", "message": {"message_id": "panel-1", "text": "...",
     "threads": [...]}}` — the user has said something in the agent panel,
     which is about the review rather than about one line: the plan, the
     tests, a file nobody commented on. Answer it with `say` (step 7). Any
     threads it points at come with it, in the same shape as a question.
   - `{"type": "round", "round": {"number": 1, "markdown": "..."}}` — the
     user has sent a round. The markdown is the review itself; address it as
     you would a finished one, then take the diff again (step 9) and keep
     waiting.
   - `{"type": "cancel", "cancel": {"message_id": "panel-1"}}` — the user has
     taken a message back. Drop what you were doing for it if you still can,
     and say nothing about it unless it is already half done.
   - `{"type": "timeout"}` — nothing was asked; wait again.
   - `{"type": "closed"}` — the review is over. Stop looping. The last round
     reached you as its own event just before this one; the background
     process also writes it to its log on the way out, which is where to
     look if you were not waiting at the time.

6. Answer in the thread it belongs to, naming the question:
   ```bash
   claude-review reply --port 8765 --thread <thread_id> --question <question_id> "..."
   ```
   A thread can have more than one question waiting at once, which is why the
   answer names one: without it the answer is filed under whatever was asked
   last. Answer from what you know about this change — why you wrote it that
   way, what you considered and rejected. That context is the reason to route
   the question to you rather than to a fresh session.

7. Answer a panel message, naming the message:
   ```bash
   claude-review say --port 8765 --message <message_id> "..."
   ```
   The panel is one conversation, so the answer lands under the message it
   names — and naming it is also what closes it: a message answered without
   its id goes on showing as worked on, with a Stop button, however much you
   have written about it elsewhere.

   Optionally, say what only you can know about yourself — the panel shows it
   beside the review's own weight, with the time it was said:
   ```bash
   claude-review status --port 8765 --model opus-5 --context "53% of 1M"
   ```
   Report it when it changes, not on every turn. Say nothing and the panel
   shows nothing, which is better than a number that is a guess.

   Leave `--message` out and you are speaking first, which is worth as much
   as answering:
   ```bash
   claude-review say --port 8765 "Both are green now — the second one needed
   the base read from the round rather than from the diff."
   ```
   Work that finished while the reader was reading is news they would
   otherwise have to come and ask for. It arrives with a dot on the header
   chip and a count in the tab title, so it reaches them in another tab.

8. Say what you are doing, while you are doing it:
   ```bash
   claude-review progress --port 8765 --message <message_id> \
     --file src/a.py --file src/b.py "rewriting the answer handler"
   ```
   Waiting says only that something is happening; this says what. Send it
   again to change it — it replaces what was showing rather than adding to
   it — and it goes away on its own when you answer, or at once with
   `--done`. `--did` and `--step` are drawn as branches of the work, so three
   subagents read as three branches rather than as a sentence about three
   subagents; the files become chips the reader can jump by.

   `--message` is optional here too: work you started for a round, or on
   your own, is worth showing under the same line. Send one whenever what
   you are doing changes — this is the third rule, and it is the only thing
   that makes a long silence readable as work.

   Two more, for what a paragraph cannot do:
   ```bash
   claude-review say --port 8765 --file src/a.py "Renamed it here."
   claude-review show --port 8765 --file src/a.py
   ```
   `say --file` offers a jump the reader takes when they want it. `show`
   takes them there and marks the file for a moment — it moves somebody
   else's screen, so send it only when they asked to be shown something.

9. After making the changes a round asked for, show them:
   ```bash
   claude-review round --port 8765
   ```
   The open review reloads the diff and moves its threads onto it: one whose
   lines survived follows them, one whose lines are gone is marked outdated
   and keeps a copy of what it was written against. What comes back names the
   files that changed since the round began — read those again rather than
   the whole diff, and the reader can put that same list on screen alone.

10. Point at a line, when what you have to say belongs on the code:
    ```bash
    claude-review point --port 8765 --file src/x.py --lines 118-130 \
      --severity question "I kept the old name here: renaming it broke two callers."
    ```
    Use it for what a paragraph in the panel would bury — where you did
    something other than what was asked, and why. It becomes an ordinary
    thread the reader answers, settles or removes, drawn as yours rather than
    as one of their marks, and it does not count as their unsent work.

    `--side old` hangs it on a line the change removed, which is the one place
    the reader cannot always write themselves: under a narrower base the left
    of the diff belongs to that base, so their gutters are shut there. Yours
    is anchored in the review's own diff and is not.

While you work, the review says when the working tree has moved on and
offers the user a "Retake" of its own. It never swaps the diff by itself, so
nothing you change under a half-written comment throws it away.

The server says nothing on its own: `claude-review --verbose <command>` puts
its diagnostic log on stderr, which is the way to see what it is doing when
a review behaves oddly. Leave it off otherwise — the quiet is deliberate.

## When there is nothing to talk about

A review you will not be attached to is one command, and it blocks until the
user sends it:

```bash
claude-review diff
```

The review is printed to stdout when they send it; read it and address each
comment. Everything above still exists on their screen — the "Ask now"
button, the panel, the offer of a round — but nothing answers, and the panel
says so when they look. So choose this only for a review you know will be
one-way: a quick look at a small change, or a machine with no way to keep a
process alive.

# Features

Everything a review does, by what you are doing at the time. How to start one is in the
[README](../README.md); the commands are in [cli.md](cli.md).

## Reading the diff

- The whole diff as one stream: every file on screen, and a file picked in the tree is scrolled to.
- Unified or split, with what changed inside a replaced line marked word by word.
- Show the lines a hunk left out, twenty at a time or all at once, or leave whitespace-only changes out.
- Read the same change, as the diff was last taken, against something else from the header: the base the review
  opened with, an earlier round of it, or any branch or tag, each with the number of files it would show. A thread
  stays where it was written; one a narrower base cannot draw is counted and listed.
- A file the agent rewrote in a round loses the tick that said you had read it.
- A moved file says where it was: "old → new" in the tree and over its code.
- Fold a file away, mark it viewed, filter the tree by path; drag the tree narrower or put it away.
- Under each file the tree lists the functions and classes the change touched: press one to go to it, or its icon to
  see where it is defined and used. The filter finds them by name too, and lists under "Not in this change" those the
  repository defines elsewhere; a toggle beside it lists the files alone.
- Ctrl+click a name in the code, Cmd+click on a Mac, and a pane by it lists where it is defined, where the change uses
  it, and where else it is used, the name marked on each line. Full reads the same places in a window, the code round the
  one chosen beside the list; "Go to symbol" takes you there, in the diff or in the file alone.
- Syntax highlighting that reads a hunk whole, so a docstring stays a docstring: JavaScript, TypeScript, Python, CSS,
  JSON, HTML and XML, shell, YAML, Markdown, Rust, Go, SQL and PHP.
- A Markdown file can be read raw, rendered, or both side by side.
- Light and dark, following the system until you choose.
- A screen reader finds the diff, each file, each thread and what is said in them. Ask your system for less motion
  and nothing moves.

## Commenting

- Comment on a line or a dragged range, on either side of the diff.
- Suggest a replacement rather than describe one.
- Mark a comment as a question or a blocker.
- Comments and answers are Markdown, with code blocks highlighted.
- Ask about a comment without leaving the review ("Ask agent now", or Alt+Enter) and read the answer in its thread.
  You can take a question back, as you can a panel message.
- Rewrite or delete what you wrote until the agent has read it.
- Resolve a thread that is settled; it goes out marked resolved.
- A "Replies" list in the header counts answers you have not read, and the tab title says so from a background tab.
- Send a round rather than end the review: the threads stay on screen, the agent answers and makes the changes, and
  the diff is taken again beneath them. A thread whose lines moved follows them; one whose lines are gone is marked
  outdated and keeps a copy of what it was written against.
- End the review instead, and everything goes to the agent as the final review.
- Comments survive a reload. A review reopened on the same repository comes back on the same port, with your unsent
  draft. A review still open is never opened twice.

## Talking to the agent

- A panel on the right for what no thread is about: the plan, the tests, a file nobody commented on. The same agent
  answers it and the threads.
- Point at a thread or any file with `@`: a thread's lines, comment and turns travel with the message.
- Paste a screenshot with Ctrl+V, in the panel or in any comment, reply or edit. The agent gets a path it can open. A
  screenshot can be the whole message.
- Two numbers, told apart: what handing the review over costs in tokens, and how much context the agent says it has
  left.
- The agent can point at a line itself: a thread in its own colour, on the code, which you answer or settle like any
  other.
- Watch what the agent is doing while it does it: a live line naming the files in hand, replaced as the work changes
  and gone when it ends.
- The agent can speak first. Work finished while you were reading arrives with a dot on the header chip, a count in
  the tab title and, if you want it, a sound.
- Jump to a file the agent names, or be taken there when you ask to be shown.
- Stop a message the agent is still working on: a request, not a kill.
- When the working tree moves on, the review says so and offers to take the diff again. It never swaps the diff under
  a comment you are writing.

## Checks

- The agent reports each run of its tests, linters and type checkers, passed or failed. A chip after the view switch
  says the worst of them: "1 of 3 failed", "2 of 3 out of date", "3 checks".
- The chip opens them: what failed first, each failure under its check, then what the code changed after.
- A failure is drawn under its line, and its file's row in the tree counts them. Press one to go to its line, read in
  where the diff left it out; `b` takes you back.
- A check is out of date once a file changes after it, measured by git's trees: a commit made after it leaves it
  current. It and its failures turn grey, and the agent is told which to run again.
- In a review of a diff only: files and a conversation have no tree to stamp a check with.

## Story

The same diff, told by the agent that made it, in the order it is best read. Press Story in the header of a diff
review.

- An overview: what was asked, what was done, and what is most worth doubting, over a diagram of the change whose
  nodes lead to its chapters. A card under it lists what was decided and why, what was turned down and what is left
  for later, each row opening on its own.
- Then the chapters, one idea each, in one scroll: why the chapter's pieces belong together, where to doubt it, and
  its steps, each a piece of one file under the agent's reason for it.
- The contents on the left list the chapters with their files and tick each one you have scrolled through.
- Nothing is left out: every changed line is in a step, in a file the agent named as housekeeping, or under "Not in
  the story".
- Every block of the agent's words offers "Ask about this", and the answer comes in its thread, as on a line.
- After a round the steps follow their code, a step whose code changed is marked, and the agent tells the story
  again.
- A story told from commits, by an agent that did not make the change, is marked reconstructed.
- A story spends the agent's tokens, so Story asks first and says what this one would cost. "Write stories without
  asking", there or under Stories in Settings, stops the asking in every review; "Write as soon as the review opens"
  has each story ready by the time you open Story.
- A review stopped and opened again keeps its story until you finish the review. You can read the files while the
  agent writes it.

How the agent is advised to tell a story, and why: [stories.md](stories.md).

## Files and plans

Review any text file: a plan, a doc, a config, source code. `/review-ui plan` opens the agent's current plan before
you approve it; from the command line, `claude-review files plan.md api.py schema.sql`. Each file is shown whole, with
one column of line numbers and syntax highlighting by its extension.

## Conversations

Review a Claude Code conversation: `/review-ui transcript` opens the current one, and
`claude-review transcript <session>.jsonl` any other; Claude Code keeps each at
`~/.claude/projects/<project>/<session-id>.jsonl`. Each message is an entry you can comment on, newest first, with
its time. Consecutive messages of one speaker are one turn, and tool calls and thinking are left out.

## Finding your way

- Your first review offers a short tour from a card in the bottom left: what you are reading, where comments go and
  how the agent answers them.
- After an update, the same card says what is new. Both are under Help (`?`).
- Send feedback, under Help: point at the part of the page you mean, read the issue to the letter, with none of your
  code in it, then open it on GitHub or hand it to your agent.

## Keys

- `j` / `k` between lines, `Enter` on a line number to comment.
- `]` / `[` between files, or between pieces of a story.
- `n` / `p` between comments, `a` to the next unread reply.
- `Ctrl+Enter` adds the comment being written, `Alt+Enter` asks the agent about it now.
- `c` talks to the agent, `f` shows or hides the file tree, `v` marks a file viewed, `u` folds it.
- `Ctrl+Shift+Enter` finishes the review, `?` lists every key.

## Settings

Layout, whitespace, theme, the sound on a new reply and when stories are written live behind the gear in the header,
and every review on the machine starts from them. They are kept in `$XDG_CONFIG_HOME/claude-review/settings.json`
(by default under `~/.config/`), and which release's news you have seen in
`$XDG_STATE_HOME/claude-review/guide.json` (by default under `~/.local/state/`).

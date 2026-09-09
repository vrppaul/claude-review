# TODO

Roadmap for the review-experience overhaul. Each item is one commit with its
tests. Remove items when done — don't check them off.

## Left from the overhaul

- [ ] `feat(ui)`: choose the base ref from the header. The server can already
      retake a diff; this is the control for it.
- [ ] `feat(ui)`: say in the review when a round changed a file nobody has a
      thread on, so a reader knows where to look next.
- [ ] `feat(ui)`: let a turn be deleted. A comment can be removed and a
      thread resolved, but a reply — the reader's or the author's — stays
      whatever it says. A duplicate answer has no way out of the thread.

## The agent panel

Designed, not built. Nine artboards, including the wire to build:
https://claude.ai/code/artifact/299299d7-7be1-4594-b0bf-5fe04425dc9e

- [ ] `feat(server)`: take a message from the panel — `POST /api/message`
      with the threads it points at, onto the same queue that carries
      questions and rounds, so one order holds for all three.
- [ ] `feat(cli)`: `claude-review say --message <id> "…"` to answer one, and
      `claude-review status --model --context` for what only the agent knows.
- [ ] `feat(ui)`: the panel itself — right side, resizable and remembered,
      turns in the thread's own vocabulary, `@thread` chips, a status strip
      that tells the review's weight apart from the agent's context, and the
      read-only state when nothing is listening.
- [ ] `feat(server)`: say when the working tree has moved on — poll
      `git status --porcelain`, push `changed`, and let the reader retake the
      diff. Never automatic: swapping the diff under someone mid-sentence
      orphans what they were writing.
- [ ] `feat(ui)`: stop a message the agent is still working on —
      `POST /api/cancel`, a request rather than a kill.

## Infrastructure

- [ ] Submit to the official Claude Code plugin marketplace

## Testing

- [ ] Drop `tmp_path` from unit tests — services should accept data in memory
      so unit tests don't touch the filesystem

## Known limits

- A single generated file of ~12,000 lines takes about 2.6s to become
  readable, because a file is built as one unit. Splitting a hunk into
  separately contained blocks was measured and made it worse. Worth
  revisiting only if such files turn up in real reviews.

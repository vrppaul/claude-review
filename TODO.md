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

## Bugs

- [ ] `fix(server)`: a review nobody ever opened lives forever. The server
      winds down when the last browser leaves, and "leaves" needs one to
      have arrived: `_ever_connected` never turns true, so a `--no-open`
      review whose URL is never opened holds its port and ~35 MB until the
      machine is rebooted. Twelve of them were found running at once. Give
      an unopened review a deadline of its own.

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

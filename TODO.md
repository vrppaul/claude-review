# TODO

Roadmap for the review-experience overhaul. Each item is one commit with its
tests. Remove items when done — don't check them off.

## Left from the overhaul

- [ ] `feat(review)`: say what a round changed, and let a version be chosen.
      One shape covers three old items: mark the files a round touched (and
      drop their "viewed" tick, which currently survives a retake), snapshot
      the working tree at each round as a git object, and let the header
      pick a base — a ref, or a round. The design was settled with Pavel and
      is written down in the `project-diff-versions-handover` memory.
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
- [ ] `fix(server)`: on SIGTERM the server releases its port but does not
      exit while a browser still holds a websocket, so a restart needs
      `kill -9`. Close the sockets as part of winding down.

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

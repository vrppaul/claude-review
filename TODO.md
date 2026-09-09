# TODO

Roadmap for the review-experience overhaul. Each item is one commit with its
tests. Remove items when done — don't check them off.

## Left from the overhaul

- [ ] `feat(server)`: tell an open review that the files changed, and offer to
      retake the diff. Deliberately a notice rather than an automatic reload:
      swapping the diff under someone mid-comment orphans what they wrote, and
      marking a comment outdated is its own piece of work.
- [ ] `feat(ui)`: choose the base ref from the header. The server can already
      retake a diff; this is the control for it.

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

# TODO

Roadmap for the review-experience overhaul. Each item is one commit with its
tests. Remove items when done — don't check them off.

## 4. Visual pass

- [ ] 4.1 `feat(ui)`: top bar — repo, branch, base, mode, counts, actions
- [ ] 4.2 `style(diff)`: new diff row treatment
- [ ] 4.3 `style(comments)`: rethink thread and composer

## 5. Review features

- [ ] 5.1 `feat(diff)`: word-level intra-line diff
- [ ] 5.2 `feat(diff)`: split view
- [ ] 5.3 `feat(diff)`: expand hidden lines between hunks
- [ ] 5.4 `feat(ui)`: keyboard layer
- [ ] 5.5 `feat(review)`: suggestion blocks
- [ ] 5.6 `feat(ui)`: whitespace toggle and comment severity

## 6. Session model

- [ ] 6.1 `feat(server)`: websocket transport, bidirectional from the start
- [ ] 6.2 `feat(ui)`: persist comment drafts
- [ ] 6.3 `feat(server)`: live reload on file changes
- [ ] 6.4 `feat(ui)`: base ref selector

## 7. Discussing a thread with Claude

- [ ] 7.1 `feat(cli)`: detached server with `wait` / `reply`
- [ ] 7.2 `feat(ui)`: discuss a thread with Claude
- [ ] 7.3 `docs(skill)`: review loop

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

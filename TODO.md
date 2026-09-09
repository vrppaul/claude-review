# TODO

Roadmap for the review-experience overhaul. Each item is one commit with its
tests. Remove items when done — don't check them off.

## 1. Output-corrupting bugs

- [ ] 1.1 `fix(diff)`: keep non-ASCII filenames — `core.quotepath=false` plus
      quoted-header parsing. Today such files vanish from the review silently.
- [ ] 1.2 `fix(review)`: anchor comments to a diff side. Adds `side` to the
      domain and schema, anchors threads by row index instead of line number,
      and disambiguates `file:42` in the output. Fixes duplicated threads.
- [ ] 1.3 `feat(diff)`: placeholder for binary and mode-only changes
- [ ] 1.4 `fix(cli)`: clean error on a busy port, plus `--version`

## 2. Design foundation

- [ ] 2.1 `style(ui)`: design tokens and code typography; collapse the double
      highlight.js theme import into one scoped theme
- [ ] 2.2 `feat(ui)`: persist theme, follow system changes, remove the flash

## 3. Continuous diff

- [ ] 3.1 `perf(ui)`: highlight a whole file once instead of line by line
- [ ] 3.2 `refactor(ui)`: extract FileSection — sticky header, collapse, viewed
- [ ] 3.3 `feat(ui)`: continuous diff stream; sidebar becomes a navigator
- [ ] 3.4 `feat(tree)`: collapsible folders, filter, viewed counter
- [ ] 3.5 `perf(ui)`: lazy row mounting for huge diffs

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

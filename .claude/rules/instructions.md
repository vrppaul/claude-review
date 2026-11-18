---
paths:
  - "AGENTS.md"
  - "CLAUDE.md"
  - ".claude/rules/*.md"
  - ".claude/agents/*.md"
---

# The instruction files

`AGENTS.md`, the rules of each area under `.claude/rules/` and the agents under `.claude/agents/`. The first two are held to their size and their paths by `scripts/check_instruction_files.py`.

## Where a line belongs

- `README.md`: what the project is; `docs/`: its features and commands in full.
- `CONTRIBUTING.md`: what a person who would contribute reads first: setting up, pull requests, a release, and the rules in short. It names these files and adds no rule.
- `TODO.md`: what is planned. `CHANGELOG.md`: what changed. The code: how a thing is built.
- `AGENTS.md`: what holds in every session, whatever file is open: how the work is done, and which file to read for what.
- A file of an area: what holds on files of one kind only. It opens with their `paths:`, and `AGENTS.md` names it.
- A file under `.claude/agents/`: how to review, and where the gates are blind. What the code or the work must be is a rule, said in the files above and never there.
- A line is written once. A second place names the first, never repeats it.

## Rules and gates

- A new rule is a new bullet a reviewer can check: never a sentence added to a paragraph.
- A rule a gate holds keeps its line where breaking it costs a rewrite: a nested function, a layer, a name. A fault a tool mends, or one edit does, needs no line.
- `CLAUDE.md` is a symlink to `AGENTS.md`: edit `AGENTS.md`.

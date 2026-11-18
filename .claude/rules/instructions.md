---
paths:
  - "AGENTS.md"
  - "CLAUDE.md"
  - ".claude/rules/*.md"
---

# The instruction files

`AGENTS.md` and the rules of each area under `.claude/rules/`. What `scripts/check_instruction_files.py` holds them to, and why, is said in its docstring.

- A new rule is a new bullet a reviewer can check, in the file of its area: never a sentence added to a paragraph.
- How a thing is built is read in its code, not said in these files.
- What a tool here can hold is a gate, not a rule; a gate of our own waits for the owner's word.
- `CLAUDE.md` is a symlink to `AGENTS.md`: edit `AGENTS.md`.

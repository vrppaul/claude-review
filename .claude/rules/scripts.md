---
paths:
  - "scripts/**"
---

# The scripts

What the project runs on itself: its gates, and its looks at its own work. How each is built is said in its docstring.

- A script's docstring says why it exists and how it is run; a tool a person runs says there what it prints and every code it exits with.
- It is run in the repository's root, and does its whole job in one process start.
- It is written as the package is: ruff, ty, vulture and `scripts/check_code_rules.py` read it as they read the package.
- One that drives the review drives it through its command line, never its modules, as an agent does: `scripts/look.py`.
- One that changes files changes a copy, never the working tree: `scripts/break_lines.py`.
- A process is started through `scripts/commands.py` alone: `scripts/check_code_rules.py` refuses one started anywhere else under `scripts/`.
- Its test runs it as it is run: as a process, in a repository of its own where it reads one (`tests/integration/test_instruction_files.py`).

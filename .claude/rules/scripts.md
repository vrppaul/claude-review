---
paths:
  - "scripts/**"
---

# The scripts

What the project runs on itself: its gates, and its looks at its own work. How each is built is said in its docstring.

- A script's docstring says why it exists, how it is run, what it prints and what it exits with.
- It does its whole job in one process start.
- It is written as the package is, and `scripts/check_code_rules.py` reads it as it reads the package.
- One that drives the review drives it through its command line, never its modules, as an agent does: `scripts/look.py`.
- One that changes files changes a copy, never the working tree: `scripts/break_lines.py`.
- A command is run through `scripts/commands.py`, the one way a script runs one.
- It is tested as it is run: as a process, by a test that names a requirement, in a repository of its own where it reads one (`tests/integration/test_instruction_files.py`).

---
paths:
  - "scripts/**"
---

# The scripts

What the project runs on itself: its gates, and its looks at its own work. How each is built is said in its docstring. These are the rules of its Python scripts: `scripts/page_check.sh` only hands a hook's work to pnpm.

- A script's docstring says why it exists and how it is run; a tool a person runs says there what it prints and every code it exits with.
- It is run in the repository's root, and does its whole job in one process start.
- It is written as the package is: ruff, ty, vulture and `scripts/check_code_rules.py` read it as they read the package, but that a script may print.
- One that drives the review drives it through its command line, never its modules, as an agent does: `scripts/look.py`.
- One that changes files changes a copy, never the working tree: `scripts/break_lines.py`.
- A command a script starts is started through `scripts/commands.py` alone: `scripts/check_code_rules.py` refuses one started anywhere else under `scripts/`. A browser is Playwright's to start and stop.
- A script that starts a command ends through `exit_code_of` of that module, so one stopped from outside stops what it started and exits 130.
- A gate's test runs it as it is run: as a process, in a repository of its own where it reads one (`tests/scripts/test_instruction_files.py`). A script that only serves or looks has a smoke test at most.

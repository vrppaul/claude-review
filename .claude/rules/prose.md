---
paths:
  - "**/*"
---

# Prose

Every word that is not code: a comment, a docstring, a document, a commit message, a report, a note handed over.

- What is not obvious gets a comment: one line that says why. What the code says, it does not say again.
- A module's docstring says why the module exists, in a few lines; any other, what the thing is for, in one. How it works is read in the code.
- What a change writes is held to these two; a longer comment or docstring already there stays until a change rewrites it.
- A comment, a docstring or a document says what stands, never what was: no "no longer", "used to", "where it was". What changed is said in a commit and in the changelog.
- No date, probe, review, session or commit hash in a comment or a docstring.
- No measurement there but the number a constant or a choice rests on, said once where it is used.
- A way not taken is one line, where the choice is made.
- A commit does the one thing its subject says, and the subject says nothing of what it replaces.
- A commit's body is for a why the subject cannot hold, in a few lines: no list of files, no tally of tests or lines.
- A sentence a reader loses nothing without is cut.

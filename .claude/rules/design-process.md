---
paths:
  - "frontend/**"
---

# How a design is made

How the page looks and answers the reader: `.claude/rules/design.md`, `.claude/rules/design-behaviour.md`.

- Before a design, load the `frontend-design` skill.
- A design starts from what the element does and every state it can be in, read from the code and from any design of it made before.
- The states to look for: whose it is, sent or not, waiting, failed, empty, folded, under the pointer, the keyboard on it, asking first, after something was taken back, a narrow window, each kind of review.
- It is drawn as a sheet of states: a row to each state, in both themes, each captioned with what changed and why.
- Variants are drawn only where the choice is open; the one chosen is then drawn in every state.
- It is drawn on the page's own markup and built stylesheet, never on a lookalike, and looked at in a shot before it is shown.
- Every size is a library part's or built from the scale of `frontend/src/styles/tokens.css` (a control plus room on the scale), never measured off a drawing.
- What a design needs and the library lacks — a size, a weight, a part — is added to the library in its own logic: named once, with the reason a reader needs it.
- Every pick is drawn on the whole page; a pick not drawn there yet is named so.
- Once the owner picks, the canvas keeps what was chosen, grouped by part, and drops the rest.

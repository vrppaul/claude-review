---
name: review
description: Open a browser-based review UI to comment on current git changes
---

Run `claude-review` to open a browser-based diff viewer where the user can review your changes and leave inline comments.

Execute this command:

```bash
uv run --project /home/pavel/projects/claude-review claude-review
```

Wait for the command to complete. When it finishes, the user has submitted their review. The formatted review comments will be printed to stdout — read them and address each comment.

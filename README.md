# Claude Review

Browser-based review tool for Claude Code. Add inline comments on code changes, text files, or conversation transcripts, and send structured feedback back to Claude.

![claude-review screenshot](docs/screenshot.png)

## Quick Start

**Option A** — cross-platform (Claude Code, Cursor, Codex, and 40+ agents):
```bash
npx skills add vrppaul/claude-review -g -y
```

**Option B** — Claude Code plugin marketplace:
```
/plugin marketplace add vrppaul/claude-review
```

Type `/review-ui` and the CLI is installed automatically on first use.

## Review Modes

### Diff mode (default)

Review current git changes in a GitHub-style diff view.

```
/review-ui
```

Shows all uncommitted changes (tracked, staged, and untracked) with two-column line numbers, add/delete highlighting, and a file tree sidebar.

### Files mode

Review any text files — plans, docs, configs, source code.

```
/review-ui plan
```

Opens the current plan file for inline review before approving. You can also review arbitrary files from the CLI:

```bash
claude-review --files plan.md
claude-review --files design.md api.py schema.sql
```

Shows files with single-column line numbers, syntax highlighting based on file extension, and a flat file list sidebar.

### Transcript mode

Review a Claude Code conversation — every user and assistant message appears as a reviewable entry.

```
/review-ui transcript
```

Opens the current session's conversation for inline review. You can also review any JSONL conversation file from the CLI:

```bash
claude-review --transcript ~/.claude/projects/<project>/<session-id>.jsonl
```

Shows messages newest-first with timestamps, merges consecutive same-role entries into turns, and filters out tool calls and thinking blocks.

### How it works

```
/review-ui (or /review-ui plan, /review-ui transcript)
  -> Server starts, browser opens
  -> You read the content, add inline comments on any line
  -> Click Submit (or Ctrl+Shift+Enter)
  -> Browser closes, formatted comments appear in Claude's context
  -> Claude reads feedback and makes the requested changes
```

## Features

- Inline comments on single lines or drag-to-select ranges
- Markdown preview — Raw, Preview (rendered), and Side-by-side view modes for `.md` files and transcripts
- Syntax highlighting (Python, TypeScript, Markdown, Rust, Go, SQL, and more)
- Comment navigation (prev/next buttons)
- Light/dark theme (auto-detects system preference, manual toggle)
- Auto-shutdown when browser tab is closed

## CLI Reference

```bash
claude-review                         # diff mode — review git changes
claude-review /path/to/repo           # diff mode — specific repository
claude-review --files file1.md        # files mode — review text files
claude-review --files a.md b.py c.rs  # files mode — multiple files
claude-review --transcript conv.jsonl # transcript mode — review conversation
claude-review --port 8080             # use specific port
claude-review --no-open               # don't open browser automatically
claude-review --verbose               # enable diagnostic logging
```

### Manual install (optional)

```bash
uv tool install git+https://github.com/vrppaul/claude-review
```

## Development

```bash
# Python
uv sync                          # install dependencies
uv run pytest                    # run all tests (unit + integration + e2e)
uv run ruff check src/ tests/    # lint
uv run ty check src/             # type check

# Frontend
cd frontend && pnpm install      # install dependencies
cd frontend && pnpm build        # build (outputs to src/claude_review/static/dist/)
cd frontend && pnpm test         # run tests
cd frontend && pnpm lint         # lint
cd frontend && pnpm check        # type check
```

## License

MIT

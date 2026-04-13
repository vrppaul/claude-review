# TODO

## Next

- [ ] Side-by-side markdown rendering — rendered markdown on one side, raw text with line numbers on the other
- [ ] Live updates — watch for file changes (FileChanged hook + WebSocket) and refresh diff in browser automatically

## Infrastructure

- [ ] Publish to PyPI — currently the skill always runs `uv tool install --upgrade git+...` which pulls latest from git on every invocation. PyPI would give proper semver, faster installs (wheels instead of git clone), and let users pin/upgrade on their own terms (`uv tool install claude-review` / `uv tool upgrade claude-review`).
- [ ] Submit to official Claude Code plugin marketplace
- [ ] Version bumping strategy (keep pyproject.toml and plugin.json in sync)

## Testing

- [ ] Eliminate `tmp_path` from unit tests — services (TextFileService, TranscriptService) should accept data in-memory so unit tests don't touch the filesystem. File reading is a thin outer layer, not the thing under test.

## Future

- [ ] Claude responding to individual comments
- [ ] Approve action
- [ ] Auto-push via Channel MCP
- [ ] Comment persistence across review rounds
- [ ] Expand hidden lines between hunks — like GitHub/GitLab's "show N hidden lines" clickable divider
- [ ] Collapse/expand file diffs
- [ ] Search within diff

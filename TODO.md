# TODO

## Next

- [ ] Overall comment — general comment box (like GitHub PR reviews), not tied to a specific line
- [ ] Transcript mode — review conversation messages (user + assistant), each message in sidebar
- [ ] Side-by-side markdown rendering — rendered markdown on one side, raw text with line numbers on the other
- [ ] Show review mode in UI — display which mode is active
- [ ] Replace argparse with click — cleaner CLI

## Transcript mode prep

When implementing `ReviewMode.TRANSCRIPT`:

- [ ] `ReviewService` — pass mode to `format_review`, use `## Transcript Review Comments` and `### User message 1:15` format
- [ ] DiffView gutter styling — `lineGutterClass()` hardcoded to diff concepts, transcript may need role-specific styling
- [ ] Frontend `ReviewMode` type — add `switch` with `never` exhaustiveness check for mode-dependent logic

## Infrastructure

- [ ] Publish to PyPI (`uvx claude-review` without git+)
- [ ] Submit to official Claude Code plugin marketplace
- [ ] Version bumping strategy (keep pyproject.toml and plugin.json in sync)

## Testing

- [ ] Component tests (CommentBox, DiffView, FileList) with @testing-library/svelte

## Future

- [ ] Live updates (FileChanged hook + WebSocket)
- [ ] Claude responding to individual comments
- [ ] Approve action
- [ ] Auto-push via Channel MCP
- [ ] Comment persistence across review rounds
- [ ] Collapse/expand file diffs
- [ ] Search within diff

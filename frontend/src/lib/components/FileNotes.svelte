<script lang="ts">
	import type { DiffFile } from '$lib/types';
	import { FILE_NOT_COMMENTABLE } from './line-commenting.svelte';

	interface Props {
		file: DiffFile;
	}

	let { file }: Props = $props();

	const modeChange = $derived(file.old_mode && file.new_mode ? `${file.old_mode} → ${file.new_mode}` : null);
	// A file can change without producing lines: binary content, or a bare
	// permission change. Say which, rather than showing an empty panel.
	const emptyReason = $derived(
		file.hunks.length > 0
			? null
			: file.is_binary
				? 'Binary file — no preview'
				: modeChange
					? 'Permission change only'
					: 'No content changes'
	);
</script>

<!-- What the lines cannot show, above whichever way the lines are drawn -->
{#if !file.commentable}
	<div data-testid="not-commentable-note" class="cr-muted border-b border-base-300 bg-base-200 px-4 py-2 text-xs">
		{FILE_NOT_COMMENTABLE}
	</div>
{/if}

{#if modeChange}
	<div data-testid="mode-change-note" class="cr-muted border-b border-base-300 bg-base-200 px-4 py-2 font-mono text-xs">
		Permission changed: {modeChange}
	</div>
{/if}

{#if emptyReason}
	<div data-testid="empty-file-note" class="cr-muted px-4 py-8 text-center text-sm">
		{emptyReason}
	</div>
{/if}

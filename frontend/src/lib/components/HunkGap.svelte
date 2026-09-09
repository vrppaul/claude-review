<script lang="ts">
	import type { DiffHunk } from '$lib/types';
	import { expansionStore } from '$lib/stores/expansions.svelte';
	import { hiddenAbove, nextWindow } from '$lib/utils/expansions';

	interface Props {
		path: string;
		hunks: DiffHunk[];
		index: number;
	}

	let { path, hunks, index }: Props = $props();

	let failed = $state<string | null>(null);
	let loading = $state(false);

	const revealed = $derived(expansionStore.revealedCount(path, index));
	const hidden = $derived(hiddenAbove(hunks, index, revealed));
	const window = $derived(nextWindow(hunks, index, revealed));
	const label = $derived(
		window === null
			? ''
			: window.end - window.start + 1 === hidden
				? `Show the ${hidden} hidden ${hidden === 1 ? 'line' : 'lines'}`
				: `Show ${window.end - window.start + 1} more of ${hidden} hidden lines`
	);

	async function reveal() {
		if (!window || loading) return;
		loading = true;
		failed = null;
		try {
			// How far the old numbering runs behind the new one at this hunk
			const oldOffset = hunks[index].old_start - hunks[index].new_start;
			await expansionStore.reveal(path, index, window.start, window.end, oldOffset);
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not read the file';
		} finally {
			loading = false;
		}
	}
</script>

{#if hidden > 0}
	<div data-testid="hunk-gap" class="flex items-center border-y border-base-300 bg-base-200">
		<button
			data-testid="expand-context"
			class="cr-expand flex w-full items-center gap-2 px-4 py-1.5 text-left font-mono text-xs"
			disabled={loading}
			onclick={reveal}
		>
			<svg class="h-3 w-3 shrink-0" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
				<path d="M6 1L3 4h2v4H3l3 3 3-3H7V4h2z" />
			</svg>
			{loading ? 'Reading…' : label}
		</button>
		{#if failed}
			<span data-testid="expand-error" class="px-4 text-xs text-error">{failed}</span>
		{/if}
	</div>
{/if}

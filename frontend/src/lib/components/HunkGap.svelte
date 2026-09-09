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
			await expansionStore.reveal(path, index, window.start, window.end);
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not read the file';
		} finally {
			loading = false;
		}
	}
</script>

{#if hidden > 0}
	<div
		data-testid="hunk-gap"
		class="flex items-center gap-3 border-y border-base-300 bg-base-200/40 px-4 py-1"
	>
		<button
			data-testid="expand-context"
			class="btn btn-ghost btn-xs font-mono text-xs text-base-content/60"
			disabled={loading}
			onclick={reveal}
		>
			{loading ? 'Reading…' : label}
		</button>
		{#if failed}
			<span data-testid="expand-error" class="text-xs text-error">{failed}</span>
		{/if}
	</div>
{/if}

<script lang="ts">
	import type { ContextGap } from '$lib/utils/expansions';
	import { messageOf } from '$lib/utils/errors';

	// What the gap says when the file could not be read and nothing said why
	const READING_FAILED = 'Could not read the file';

	interface Props {
		/** What the diff left out above the hunk. */
		gap: ContextGap;
		/** The hunk's own header, which says where it is in the file. */
		header: string;
		/** Read in the next lines of the gap. */
		onReveal: (gap: ContextGap) => Promise<void>;
	}

	let { gap, header, onReveal }: Props = $props();

	let failed = $state<string | null>(null);
	let loading = $state(false);

	const windowSize = $derived(gap.next === null ? 0 : gap.next.end - gap.next.start + 1);
	const label = $derived(
		windowSize === gap.hidden
			? `Show the ${gap.hidden} hidden ${gap.hidden === 1 ? 'line' : 'lines'}`
			: `Show ${windowSize} more of ${gap.hidden} hidden lines`
	);

	async function reveal() {
		if (loading) return;
		loading = true;
		failed = null;
		try {
			await onReveal(gap);
		} catch (error) {
			failed = messageOf(error, READING_FAILED);
		} finally {
			loading = false;
		}
	}
</script>

<!-- The jump and what it says are one thing: with nothing hidden above this
	hunk the code runs on unbroken, and a marker saying otherwise is a line of
	punctuation in the middle of a sentence. -->
{#if gap.hidden > 0}
	{#if header}
		<div data-testid="hunk-header" class="cr-muted border-y border-base-300 bg-base-200 px-4 py-1 font-mono text-xs">
			{header}
		</div>
	{/if}
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

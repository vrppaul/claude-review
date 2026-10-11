<script lang="ts">
	import type { ContextGap } from '$lib/utils/expansions';
	import { messageOf } from '$lib/utils/errors';
	import { counted } from '$lib/utils/words';
	import type { FileDrawing } from './file-drawing.svelte';
	import Icon from './Icon.svelte';

	// What the gap says when the file could not be read and nothing said why
	const READING_FAILED = 'Could not read the file';

	interface Props {
		/** What the diff left out above the hunk. */
		gap: ContextGap;
		/** The hunk's own header, which says where it is in the file. */
		header: string;
		/** The file the gap is in, which reads the gap in where it may be, and says when it is reading. */
		drawing: FileDrawing;
	}

	let { gap, header, drawing }: Props = $props();

	let failed = $state<string | null>(null);

	const reading = $derived(drawing.isReading(gap));
	const windowSize = $derived(gap.next === null ? 0 : gap.next.end - gap.next.start + 1);
	// What a gap that is not read into says of itself
	const unchanged = $derived(counted(gap.hidden, 'unchanged line', 'unchanged lines'));
	const hidden = $derived(counted(gap.hidden, 'hidden line', 'hidden lines'));
	const label = $derived(windowSize === gap.hidden ? `Show the ${hidden}` : `Show ${windowSize} more of ${hidden}`);

	async function reveal() {
		failed = null;
		try {
			await drawing.read(gap);
		} catch (error) {
			failed = messageOf(error, READING_FAILED);
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
		{#if drawing.readsGaps}
			<button
				data-testid="expand-context"
				class="cr-expand flex w-full items-center gap-2 px-4 py-1.5 text-left font-mono text-xs"
				disabled={reading}
				onclick={reveal}
			>
				<Icon name="expand" class="h-3 w-3 shrink-0" />
				{reading ? 'Reading…' : label}
			</button>
			{#if failed}
				<span data-testid="expand-error" class="px-4 text-xs text-error">{failed}</span>
			{/if}
		{:else}
			<span class="cr-muted px-4 py-1.5 font-mono text-xs">⋯ {unchanged}</span>
		{/if}
	</div>
{/if}

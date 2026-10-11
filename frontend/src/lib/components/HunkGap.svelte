<script lang="ts">
	import { type ContextGap, EXPAND_STEP, type GapRead, hiddenIn, sizeOf } from '$lib/utils/expansions';
	import { messageOf } from '$lib/utils/errors';
	import { counted } from '$lib/utils/words';
	import type { FileDrawing } from './file-drawing.svelte';
	import Icon from './Icon.svelte';

	// What the gap says when the file could not be read and nothing said why
	const READING_FAILED = 'Could not read the file';

	interface Props {
		/** What the diff left out above a hunk, between two, or below the last. */
		gap: ContextGap;
		/** The header of the hunk below it, which says where that hunk is in the file; empty below the last. */
		header: string;
		/** The file the gap is in, which reads the gap in where it may be, and says when it is reading. */
		drawing: FileDrawing;
	}

	let { gap, header, drawing }: Props = $props();

	let failed = $state<string | null>(null);

	const reading = $derived(drawing.isReading(gap));
	const hidden = $derived(hiddenIn(gap));
	// A gap this short is read whole in one go; a longer one a step up from
	// the change below it, a step down from the change above, or all at once
	const inOneGo = $derived(hidden !== null && hidden <= EXPAND_STEP ? drawing.readOf(gap, 'all') : null);
	const stepUp = $derived(inOneGo ? null : drawing.readOf(gap, 'up'));
	const stepDown = $derived(inOneGo ? null : drawing.readOf(gap, 'down'));
	const allAtOnce = $derived(inOneGo ? null : drawing.readOf(gap, 'all'));
	// Drawn while lines are hidden; below the last hunk, where how many is not
	// known yet, only where they can be read in to find out
	const drawn = $derived(hidden === null ? drawing.readsGaps : hidden > 0);
	// What a gap says of itself: how much it hides, as far as that is known
	const unchanged = $derived(counted(hidden ?? 0, 'unchanged line', 'unchanged lines'));
	const hiddenLines = $derived(
		hidden === null ? 'The file may go on below' : counted(hidden, 'hidden line', 'hidden lines')
	);

	async function widen(read: GapRead) {
		failed = null;
		try {
			await drawing.read(read);
		} catch (error) {
			failed = messageOf(error, READING_FAILED);
		}
	}
</script>

<!-- The jump and what it says are one thing: with nothing hidden above this
	hunk the code runs on unbroken, and a marker saying otherwise is a line of
	punctuation in the middle of a sentence. -->
{#if drawn}
	{#if header}
		<div data-testid="hunk-header" class="cr-muted border-y border-base-300 bg-base-200 px-4 py-1 font-mono text-xs">
			{header}
		</div>
	{/if}
	<div data-testid="hunk-gap" class="flex items-center gap-1 border-y border-base-300 bg-base-200 font-mono text-xs">
		{#if drawing.readsGaps}
			{#if inOneGo}
				<button
					type="button"
					data-testid="expand-all"
					class="cr-expand flex w-full items-center gap-2 px-4 py-1.5 text-left"
					disabled={reading}
					onclick={() => widen(inOneGo)}
				>
					<Icon name="expand" class="h-3 w-3 shrink-0" />
					{reading ? 'Reading…' : `Show the ${hiddenLines}`}
				</button>
			{:else}
				<span class="cr-muted flex flex-1 items-center gap-2 px-4 py-1.5">
					<Icon name="expand" class="h-3 w-3 shrink-0" />
					{reading ? 'Reading…' : hiddenLines}
				</span>
				{#if stepUp}
					{@const said = `Show ${sizeOf(stepUp)} more lines, up from the change below`}
					<button
						type="button"
						data-testid="expand-up"
						class="cr-expand px-3 py-1.5"
						title={said}
						aria-label={said}
						disabled={reading}
						onclick={() => widen(stepUp)}
					>
						↑ {sizeOf(stepUp)}
					</button>
				{/if}
				{#if stepDown}
					{@const said = `Show ${sizeOf(stepDown)} more lines, down from the change above`}
					<button
						type="button"
						data-testid="expand-down"
						class="cr-expand px-3 py-1.5"
						title={said}
						aria-label={said}
						disabled={reading}
						onclick={() => widen(stepDown)}
					>
						↓ {sizeOf(stepDown)}
					</button>
				{/if}
				{#if allAtOnce}
					<!-- As many as one read of the file hands back: every hidden line, unless there are more -->
					<button
						type="button"
						data-testid="expand-all"
						class="cr-expand px-3 py-1.5"
						disabled={reading}
						onclick={() => widen(allAtOnce)}
					>
						{sizeOf(allAtOnce) === hidden ? 'Show all' : `Show ${sizeOf(allAtOnce)}`}
					</button>
				{/if}
			{/if}
			{#if failed}
				<span data-testid="expand-error" class="px-4 text-error">{failed}</span>
			{/if}
		{:else}
			<span class="cr-muted px-4 py-1.5">⋯ {unchanged}</span>
		{/if}
	</div>
{/if}

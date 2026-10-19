<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import { useReview } from '$lib/review/context';
	import BreathingDots from '$lib/ui/BreathingDots.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import { type ContextGap, EXPAND_STEP, type GapRead, hiddenIn, sizeOf } from '$lib/utils/expansions';
	import { messageOf } from '$lib/utils/errors';
	import { placeKey } from '$lib/utils/line-places';
	import { counted, type CountedWords } from '$lib/utils/words';
	import type { FileDrawing } from './file-drawing.svelte';

	// What the lines a gap hides are called, counted, where they may be read in; and what is said below the last
	// hunk of a file whose length the diff does not tell
	const HIDDEN_LINES: CountedWords = { one: 'hidden line', many: 'hidden lines' };
	const MAY_GO_ON_BELOW = 'The file may go on below';

	interface Props {
		/** What the diff left out above a hunk, between two, or below the last. */
		gap: ContextGap;
		/** The header of the hunk below it, which says where that hunk is in the file; empty below the last. */
		header: string;
		/** The file the gap is in, which reads the gap in where it may be, and says when it is reading. */
		drawing: FileDrawing;
	}

	let { gap, header, drawing }: Props = $props();
	const review = useReview();

	let failed = $state<string | null>(null);

	const reading = $derived(drawing.isReading(gap));
	const hidden = $derived(hiddenIn(gap));
	// A gap this short is read whole in one go; a longer one a step up from
	// the change below it, a step down from the change above, or all at once
	const inOneGo = $derived(hidden !== null && hidden <= EXPAND_STEP ? drawing.readOf(gap, 'all') : null);
	const stepUp = $derived(inOneGo ? null : drawing.readOf(gap, 'up'));
	const stepDown = $derived(inOneGo ? null : drawing.readOf(gap, 'down'));
	const allAtOnce = $derived(inOneGo ? null : drawing.readOf(gap, 'all'));
	// Drawn where the gap is the drawing's to say, while it hides lines or may
	const drawn = $derived(drawing.draws(gap));
	// The words for the lines a gap hides where it is only said, in a piece
	// of a file; null where the lines may be read in instead, and the gap
	// then says how many it hides, as far as that is known
	const onlySaid = $derived(drawing.saidOfAGap);
	const hiddenLines = $derived(hidden === null ? MAY_GO_ON_BELOW : counted(hidden, HIDDEN_LINES));

	/**
	 * Read lines into the gap. The button pressed keeps the keyboard while
	 * lines are still hidden; read whole, the gap and its bar go, and the
	 * keyboard goes to the first line shown where they were.
	 */
	async function widen(read: GapRead, pressed: HTMLElement) {
		failed = null;
		try {
			await drawing.read(read);
		} catch (error) {
			failed = messageOf(error);
			return;
		}
		const firstShown = placeKey({ side: 'new', number: read.window.start });
		focusWhatRemains(() => (pressed.isConnected ? pressed : review.sections.lineOrFile(drawing.path(), firstShown)));
	}
</script>

<!-- The jump and what it says are one thing: with nothing hidden above this
	hunk the code runs on unbroken, and a marker saying otherwise is a line of
	punctuation in the middle of a sentence. What is drawn here is counted
	before it is drawn, by `roomOf`: a change to what is drawn changes it too. -->
<!-- What the gap says of the lines it leaves out: that they are being read, while they are, or how many it hides -->
{#snippet readingOr(said: string)}
	{#if reading}
		<BreathingDots tone="inherited" testId="reading-dots" />
		Reading
	{:else}
		<Icon name="expand" size="xs" />
		{said}
	{/if}
{/snippet}

{#if drawn}
	{#if header}
		<div data-testid="hunk-header" class="cr-hunk-header cr-muted bg-base-200 font-mono text-xs">{header}</div>
	{/if}
	<div data-testid="hunk-gap" class="cr-hunk-gap gap-1 bg-base-200 font-mono text-xs">
		{#if onlySaid}
			<span class="cr-muted flex items-center px-4">⋯ {counted(hidden ?? 0, onlySaid)}</span>
		{:else}
			{#if inOneGo}
				<button
					type="button"
					data-testid="expand-all"
					class="cr-expand cr-pressable flex w-full items-center gap-2 px-4 text-left"
					disabled={reading}
					onclick={(event) => widen(inOneGo, event.currentTarget)}
				>
					{@render readingOr(`Show the ${hiddenLines}`)}
				</button>
			{:else}
				<span class="cr-muted flex flex-1 items-center gap-2 px-4">
					{@render readingOr(hiddenLines)}
				</span>
				{#if stepUp}
					{@const said = `Show ${sizeOf(stepUp)} more lines, up from the change below`}
					<button
						type="button"
						data-testid="expand-up"
						class="cr-expand cr-pressable px-3"
						title={said}
						aria-label={said}
						disabled={reading}
						onclick={(event) => widen(stepUp, event.currentTarget)}
					>
						↑ {sizeOf(stepUp)}
					</button>
				{/if}
				{#if stepDown}
					{@const said = `Show ${sizeOf(stepDown)} more lines, down from the change above`}
					<button
						type="button"
						data-testid="expand-down"
						class="cr-expand cr-pressable px-3"
						title={said}
						aria-label={said}
						disabled={reading}
						onclick={(event) => widen(stepDown, event.currentTarget)}
					>
						↓ {sizeOf(stepDown)}
					</button>
				{/if}
				{#if allAtOnce}
					<!-- As many as one read of the file hands back: every hidden line, unless there are more -->
					<button
						type="button"
						data-testid="expand-all"
						class="cr-expand cr-pressable px-3"
						disabled={reading}
						onclick={(event) => widen(allAtOnce, event.currentTarget)}
					>
						{sizeOf(allAtOnce) === hidden ? 'Show all' : `Show ${sizeOf(allAtOnce)}`}
					</button>
				{/if}
			{/if}
			{#if failed}
				<span data-testid="expand-error-room" class="flex min-w-0 items-center px-4">
					<Failure stands="cut" testId="expand-error" said={failed} />
				</span>
			{/if}
		{/if}
	</div>
{/if}

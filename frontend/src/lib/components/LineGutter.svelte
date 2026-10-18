<script lang="ts">
	import type { LineSide } from '$lib/types';
	import { lineInWords } from '$lib/anchors/line-label';
	import { LINE_NUMBER_ROLE } from '$lib/dom/keyboard';
	import type { DrawnLine } from '$lib/utils/drawn-file';
	import type { LineCommenting, Reach } from './line-commenting.svelte';

	// A click a pointer made says how many presses made it; one with none
	// came from the keyboard — Enter or Space on the button — or from
	// assistive technology or voice control, which click without pressing
	const PRESSLESS_CLICK = 0;

	interface Props {
		drawn: DrawnLine;
		/** Which side's number it shows: a line the change kept has one on each. */
		side: LineSide;
		reach: Reach;
		commenting: LineCommenting;
	}

	let { drawn, side, reach, commenting }: Props = $props();

	const shown = $derived(side === 'old' ? drawn.line.old_number : drawn.line.new_number);
	const isRowStop = $derived(reach === 'row-stop');
	// The same line as the row's stop beside it: a target for the pointer, said once, by that stop
	const pointerOnly = $derived(reach === 'pointer');
	// A number that takes no comment says why, but is not disabled: the browser
	// moves no focus onto a disabled button, and j and k would stop at it for good
	const refusal = $derived(commenting.whyNot(drawn.place));

	/**
	 * A click with no press behind it opens the comment field on the line. A
	 * pointer's press has already picked the line — a drag starts with it —
	 * and its click adds nothing.
	 */
	function commentOnClick(event: MouseEvent) {
		if (event.detail === PRESSLESS_CLICK) commenting.commentOn(drawn);
	}
</script>

<!-- A side the line has no number on draws none: nothing there to press or to stop at -->
{#if shown !== null}
	<button
		type="button"
		data-testid={isRowStop ? 'line-gutter' : 'old-line-gutter'}
		data-role={isRowStop ? LINE_NUMBER_ROLE : undefined}
		data-place={pointerOnly ? undefined : drawn.key}
		data-tour={isRowStop ? 'line-number' : undefined}
		class="cr-gutter-button cr-pressable"
		tabindex={pointerOnly ? -1 : 0}
		aria-hidden={pointerOnly ? 'true' : undefined}
		aria-label="Comment on {lineInWords(drawn.place)}"
		aria-disabled={refusal === null ? undefined : 'true'}
		title={refusal ?? undefined}
		onmousedown={() => commenting.press(drawn)}
		onclick={commentOnClick}
	>
		{shown}
	</button>
{/if}

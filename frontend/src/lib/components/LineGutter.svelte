<script lang="ts" module>
	/**
	 * How the keyboard reaches a line's number. Every row has one stop, which
	 * j and k move between and Tab reaches too: its new number, or its old one
	 * where it shows no new one. The old number beside a new one is reached by
	 * Tab when it is another line — a removed line facing the line that
	 * replaced it — and left to the mouse when it is the same line.
	 */
	export type Reach = 'row-stop' | 'tab' | 'pointer';
</script>

<script lang="ts">
	import type { LineSide } from '$lib/types';
	import { lineInWords } from '$lib/anchors/line-label';
	import { LINE_NUMBER_ROLE } from '$lib/dom/keyboard';
	import type { DrawnLine } from '$lib/utils/drawn-file';
	import type { LineCommenting } from './line-commenting.svelte';

	// What a number that takes no comment says when asked why
	const NOT_THE_REVIEWS = 'A removed line belongs to the base on screen. Show the whole diff to write here.';

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
	// A number that takes no comment says so, but is not disabled: the browser
	// moves no focus onto a disabled button, and j and k would stop at it for good
	const writable = $derived(commenting.mayComment(drawn.place));

	/** Enter or Space on a line's number opens the comment field there. */
	function commentOnKey(event: KeyboardEvent) {
		if (event.key !== 'Enter' && event.key !== ' ') return;
		event.preventDefault();
		commenting.commentOn(drawn);
	}
</script>

<!-- A side the line has no number on draws none: nothing there to press or to stop at -->
{#if shown !== null}
	<button
		type="button"
		data-testid={isRowStop ? 'line-gutter' : 'old-line-gutter'}
		data-role={isRowStop ? LINE_NUMBER_ROLE : undefined}
		data-tour={isRowStop ? 'line-number' : undefined}
		class="cr-gutter-button"
		tabindex={reach === 'pointer' ? -1 : 0}
		aria-label="Comment on {lineInWords(drawn.place)}"
		aria-disabled={writable ? undefined : 'true'}
		title={writable ? undefined : NOT_THE_REVIEWS}
		onmousedown={() => commenting.press(drawn)}
		onkeydown={commentOnKey}
	>
		{shown}
	</button>
{/if}

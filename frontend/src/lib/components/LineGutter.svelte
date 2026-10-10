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
		/** Whether the keyboard stops here. One number a row is a stop; the other is for the mouse. */
		stop: boolean;
		commenting: LineCommenting;
	}

	let { drawn, side, stop, commenting }: Props = $props();

	const shown = $derived(side === 'old' ? drawn.line.old_number : drawn.line.new_number);
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

<button
	data-testid={stop ? 'line-gutter' : 'old-line-gutter'}
	data-role={stop ? LINE_NUMBER_ROLE : undefined}
	data-tour={stop ? 'line-number' : undefined}
	class="cr-gutter-button"
	tabindex={stop ? 0 : -1}
	aria-label="Comment on {lineInWords(drawn.place)}"
	aria-disabled={writable ? undefined : 'true'}
	title={writable ? undefined : NOT_THE_REVIEWS}
	onmousedown={() => commenting.press(drawn)}
	onkeydown={commentOnKey}
>
	{shown ?? ''}
</button>

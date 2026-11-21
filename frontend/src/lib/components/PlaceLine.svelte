<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		/** The number of the line the place is on. */
		number: number;
		/** The line, highlighted, with what it is listed for marked on it. */
		markup: string;
		/** Whether the change wrote the line: it is drawn in the change's tint and edge, as the diff draws it. */
		written: boolean;
		/** Where places are chosen, whether this one is: its code stands beside the list. */
		chosen?: boolean;
		/** Where places are chosen, choose this one: its row pressed anywhere, or the keyboard come to its way. */
		choose?: (() => void) | undefined;
		testId: string;
		/** The way to the place, at the row's end. */
		act: Snippet;
	}

	let { number, markup, written, chosen = false, choose, testId, act }: Props = $props();

	/** A press on the way to the place is no press on its row. */
	function keepFromTheRow(event: MouseEvent) {
		event.stopPropagation();
	}
</script>

<!-- One place in a file, a row of a table of them: its line's number, the line drawn by the rules a diff's line is,
	on one line of its own cut where the room ends, and the way to it. Where places are chosen, the row is pressed
	to choose it, and the keyboard choosing its way is the keyboard's way to it. A press on the way itself is the
	way's alone: it takes the reader off, the window gone by then, and chooses nothing -->
<tr
	data-testid={testId}
	class={['cr-row', written && 'cr-row-add', choose && 'cr-place-choosable', chosen && 'cr-place-chosen']}
	onclick={choose}
	onfocusin={choose}
>
	<td class="cr-gutter cr-place-number">{number}</td>
	<td class="cr-code-cell cr-place-code">{@html markup}</td>
	<td class="cr-place-act" onclick={keepFromTheRow}>{@render act()}</td>
</tr>

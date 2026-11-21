<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		/** The number of the line the place is on. */
		number: number;
		/** The line, highlighted, with what it is listed for marked on it. */
		markup: string;
		/** Whether the change wrote the line: it is drawn in the change's tint and edge, as the diff draws it. */
		written: boolean;
		testId: string;
		/** The way to the place, at the row's end. */
		act: Snippet;
	}

	let { number, markup, written, testId, act }: Props = $props();
</script>

<!-- One place in a file, a row of a table of them: its line's number, the line drawn by the rules a diff's line is,
	on one line of its own cut where the room ends, and the way to it -->
<tr data-testid={testId} class={['cr-row', written && 'cr-row-add']}>
	<td class="cr-gutter cr-place-number">{number}</td>
	<td class="cr-code-cell cr-place-code">{@html markup}</td>
	<td class="cr-place-act">{@render act()}</td>
</tr>

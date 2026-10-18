<script lang="ts">
	import { dragEdge, stepEdge, type ColumnWidth, type Grows } from '$lib/dom/resize';

	// Which edge of the column the grip sits on: the one the column grows towards
	const EDGES: Record<Grows, string> = { left: 'cr-grip-left', right: 'cr-grip-right' };

	interface Props {
		/** The column the grip sizes. */
		column: ColumnWidth;
		/** Which way the column grows: towards the edge the grip sits on. */
		grows: Grows;
		/** What the grip resizes, said to whoever cannot see it. */
		label: string;
		testId: string;
	}

	let { column, grows, label, testId }: Props = $props();
</script>

<!-- The reader's own width, dragged or stepped with the arrow keys: a splitter
	between the column and the diff, which says how wide the column is -->
<div
	role="separator"
	tabindex="0"
	data-testid={testId}
	class={['cr-grip', EDGES[grows]]}
	aria-label={label}
	aria-orientation="vertical"
	aria-valuenow={column.width}
	aria-valuemin={column.least}
	aria-valuemax={column.most}
	onpointerdown={(event) => dragEdge(event, column, grows)}
	onkeydown={(event) => stepEdge(event, column, grows)}
></div>

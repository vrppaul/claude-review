<script lang="ts">
	import { dragEdge, stepEdge, type Grows, type Sizing } from '$lib/dom/resize';

	// Which edge of the column the grip sits on: the one the column grows towards
	const EDGES: Record<Grows, string> = { left: 'cr-grip-left', right: 'cr-grip-right' };

	interface Props {
		/** How wide the column is, which way it grows, and who is told its new width. */
		sizing: Sizing;
		/** What the grip resizes, said to whoever cannot see it. */
		label: string;
		testId: string;
	}

	let { sizing, label, testId }: Props = $props();
</script>

<!-- The reader's own width, dragged or stepped with the arrow keys -->
<button
	type="button"
	data-testid={testId}
	class="cr-grip {EDGES[sizing.grows]}"
	aria-label={label}
	onpointerdown={(event) => dragEdge(event, sizing)}
	onkeydown={(event) => stepEdge(event, sizing)}
></button>

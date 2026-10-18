<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		/** What its segments pick between, said to whoever cannot see them. */
		label: string;
		testId: string;
		/** Its segments, each a `Segment`. */
		children: Snippet;
	}

	let { label, testId, children }: Props = $props();
</script>

<!-- A track of segments, the one picked marked on it: what is picked here is a way of reading, not an act -->
<div data-testid={testId} class="cr-ui-segmented" role="group" aria-label={label}>
	{@render children()}
</div>

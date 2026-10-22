<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		testId: string;
		/** Its lists, a ListsCardRow to each. */
		children: Snippet;
	}

	let { testId, children }: Props = $props();
</script>

<!-- Lists on one card, a row to each, on columns the rows share, so each part of a row stands on one edge with the
	same part of every other: a list's name, its words, its fold. Narrow, each list's name stands over its words -->
<div data-testid={testId} class="cr-ui-lists-card">{@render children()}</div>

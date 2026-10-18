<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		testId: string;
		/** What heads the column, and its controls: the way to put it away at the far end. */
		children: Snippet;
	}

	let { testId, children }: Props = $props();
</script>

<!-- The bar a column beside what is read is headed by, the same in each: above what scrolls in it, so its
	heading and the way to put it away stay in sight -->
<header data-testid={testId} class="cr-ui-column-bar">
	{@render children()}
</header>

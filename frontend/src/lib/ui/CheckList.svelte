<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		testId: string;
		/** Its checks, each a CheckRow, those of an earlier code together in OutOfDateChecks. */
		children: Snippet;
	}

	let { testId, children }: Props = $props();
</script>

<!-- The checks the agent reported, in one grid: each check's mark, name, words and time stand in a column each,
	whichever group it stands in -->
<ul data-testid={testId} class="cr-ui-checks">
	{@render children()}
</ul>

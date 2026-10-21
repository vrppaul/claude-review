<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		testId: string;
		/** Its acts, each a MenuItem. */
		children: Snippet;
	}

	let { testId, children }: Props = $props();
</script>

<!-- What can be done to a thing, offered in the pane its control opens: its acts one under another, as wide as the
	widest of their names -->
<div data-testid={testId} class="cr-ui-menu">{@render children()}</div>

<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		testId: string;
		/** What stands one under another: blocks the reader may ask about, each a `Band`, and what stands among them. */
		children: Snippet;
	}

	let { testId, children }: Props = $props();
</script>

<!-- Blocks the reader may ask about, one under another, as close as cards in a stack (lib/ui/frame.ts) -->
<div data-testid={testId} class="cr-ui-bands">{@render children()}</div>

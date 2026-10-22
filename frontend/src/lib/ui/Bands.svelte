<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		/** Whether they stand under words that head them, a chapter's title, which they keep as far from as from one another. */
		headed?: boolean;
		testId: string;
		/** What stands one under another: blocks the reader may ask about, each a `Band`, and what stands among them. */
		children: Snippet;
	}

	let { headed = false, testId, children }: Props = $props();
</script>

<!-- Blocks the reader may ask about, one under another, as far apart as the offer over a band is tall, so the
	offer lies over none of the words above it, or as close as cards in a stack where each block is a card holding
	its offer inside (lib/ui/frame.ts) -->
<div data-testid={testId} class={['cr-ui-bands', headed && 'cr-ui-bands-headed']}>{@render children()}</div>

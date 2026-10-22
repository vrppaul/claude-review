<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		/** Whether they are a list, each standing in an `<li>` of its own: the things an overview lists. */
		listed?: boolean;
		/** Whether they stand under words that head them, a chapter's title, which they keep as far from as from one another. */
		headed?: boolean;
		testId: string;
		/** What stands one under another: blocks the reader may ask about, each a `Band`, and what stands among them. */
		children: Snippet;
	}

	let { listed = false, headed = false, testId, children }: Props = $props();

	const laidOut = $derived(['cr-ui-bands', headed && 'cr-ui-bands-headed']);
</script>

<!-- Blocks the reader may ask about, one under another, as far apart as the offer over a band is tall, so the
	offer lies over none of the words above it, or as close as cards in a stack where each block is a card holding
	its offer inside (lib/ui/frame.ts) -->
{#if listed}
	<ul data-testid={testId} class={laidOut}>{@render children()}</ul>
{:else}
	<div data-testid={testId} class={laidOut}>{@render children()}</div>
{/if}

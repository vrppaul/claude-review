<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		testId: string;
		/** Where what the card holds hangs: a sign and a line, a block of the story's words. */
		place: Snippet;
		/** What follows the place: what it asks for, where it stands, and, folded, what it holds (FoldedSummary). */
		children?: Snippet | undefined;
		/** What can be done to what the card holds, at the bar's end, its fold's chevron last. */
		end: Snippet;
	}

	let { testId, place, children, end }: Props = $props();
</script>

<!-- The bar heading a card (Card's bar): what the card holds and where it stands, then what can be done to it, the
	same open and folded. As tall as every head on the row under the header; on the tone's wash, ruled off from what
	is under it while the card stands open (lib/ui/card.ts) -->
<div data-testid={testId} class="cr-ui-card-bar">
	<span class="cr-ui-card-bar-place">{@render place()}</span>
	{@render children?.()}
	<div class="cr-ui-card-bar-end">{@render end()}</div>
</div>

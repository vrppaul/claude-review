<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		testId: string;
		/** What stands at the row's start, apart from the acts: what a note says, the keys that take the main act, a tool for what is written. */
		aside?: Snippet | undefined;
		/** What stands just before the main act: the other acts, and why the main one failed, where it did. */
		others?: Snippet | undefined;
		/** The one act the row leads to, drawn last: primary, or danger where it loses what was written. */
		main: Snippet;
	}

	let { testId, aside, others, main }: Props = $props();
</script>

<!-- The acts that end a pane, a card, a question, a field being written, a note or a view's wait, in one order
	everywhere: what stands aside of them at the row's start, then the others, and the act the row leads to last,
	at its far end. Every act is a snippet, so none can stand anywhere else; every button in the row stands at
	one height, the others quiet or asking beside the main one, which is the one primary or danger (eslint) -->
<div data-testid={testId} class="cr-ui-actions">
	{#if aside}
		<div class="cr-ui-actions-aside">{@render aside()}</div>
	{/if}
	{@render others?.()}
	{@render main()}
</div>

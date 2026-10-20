<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		testId: string;
		/** What stands at the row's start, apart from the acts: the keys that take the main one, a tool for what is written. */
		aside?: Snippet | undefined;
		/** What stands just before the main act: the other acts, and why the main one failed, where it did. */
		others?: Snippet | undefined;
		/** The one act the row leads to, last: primary, or danger where it loses what was written. */
		children: Snippet;
	}

	let { testId, aside, others, children }: Props = $props();
</script>

<!-- The acts that end a pane, a card, a question or a field being written, in one order everywhere: what stands
	aside of them at the row's start, then the others, and the act the row leads to last, at its far end. Every
	button in it stands at one height, the others quiet or asking beside the main one (eslint) -->
<div data-testid={testId} class="cr-ui-actions">
	{#if aside}
		<div class="cr-ui-actions-aside">{@render aside()}</div>
	{/if}
	{@render others?.()}
	{@render children()}
</div>

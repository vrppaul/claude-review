<script lang="ts">
	import type { Snippet } from 'svelte';

	/** Where a link leads: out of the review, to an address; or nowhere, doing something in place, as a button does. */
	type Goes = { href: string } | { onclick: () => void };

	type Props = Goes & {
		testId: string;
		/** The link itself, for whoever hands the keyboard to it: the first way a pane lists, as the pane fills. */
		element?: HTMLElement | undefined;
		/** Its words, at the size of the line they stand in. */
		children: Snippet;
	};

	let { testId, element = $bindable(), children, ...goes }: Props = $props();
</script>

<!-- Words that lead somewhere or do something, in the colour of the reader's controls as words. One that leads
	out of the review opens in a tab of its own, so the review stays open, and tells the page it opens nothing of
	where it came from -->
{#if 'href' in goes}
	<a
		bind:this={element}
		data-testid={testId}
		class="cr-ui-link"
		href={goes.href}
		target="_blank"
		rel="noopener noreferrer"
	>
		{@render children()}
	</a>
{:else}
	<button bind:this={element} type="button" data-testid={testId} class="cr-ui-link" onclick={goes.onclick}>
		{@render children()}
	</button>
{/if}

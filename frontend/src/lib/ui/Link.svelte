<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * Where a link leads: out of the review, to an address, with what the page does as the reader follows it, where
	 * it does anything; or nowhere, doing something in place, as a button does.
	 */
	type Goes = { href: string; onfollow?: (() => void) | undefined } | { onclick: () => void };

	type Props = Goes & {
		testId: string;
		/** Its words, at the size of the line they stand in. */
		children: Snippet;
	};

	let { testId, children, ...goes }: Props = $props();
</script>

<!-- Words that lead somewhere or do something, in the colour of the reader's controls as words. One that leads
	out of the review opens in a tab of its own, so the review stays open, and tells the page it opens nothing of
	where it came from -->
{#if 'href' in goes}
	<a
		data-testid={testId}
		class="cr-ui-link"
		href={goes.href}
		target="_blank"
		rel="noopener noreferrer"
		onclick={goes.onfollow}
	>
		{@render children()}
	</a>
{:else}
	<button type="button" data-testid={testId} class="cr-ui-link" onclick={goes.onclick}>
		{@render children()}
	</button>
{/if}

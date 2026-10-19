<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		/** Inside a thread or the panel: set in a comment's reading face. */
		dense?: boolean;
		testId: string;
		/** The words written in Markdown, drawn as the page draws them. */
		children: Snippet;
	}

	let { dense = false, testId, children }: Props = $props();
</script>

<!-- Words written in Markdown, drawn at a comment's measure: their links as every link of the page is (Link) -->
<div data-testid={testId} class={['cr-ui-prose prose prose-sm', dense && 'cr-comment-body']}>
	{@render children()}
</div>

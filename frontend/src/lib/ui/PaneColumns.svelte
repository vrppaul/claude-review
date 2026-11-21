<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		testId: string;
		/** The list, at the pane's start, scrolling down by itself. */
		list: Snippet;
		/** What heads what is chosen, kept above it. */
		besideHead: Snippet;
		/** What is chosen in the list, read beside it under its head, scrolling both ways by itself. */
		beside: Snippet;
		/** What is chosen, as a screen reader names the column the keyboard scrolls. */
		besideLabel: string;
	}

	let { testId, list, besideHead, beside, besideLabel }: Props = $props();
</script>

<!-- What a pane as large as the window holds in two columns: a list at its start, at one width whatever the
	window's, and what is chosen in it filling the rest on the reading ground, under its head. Each scrolls by
	itself, so choosing never moves the list; a line too long for its column is cut at the column's edge, the column
	scrolling sideways to it. What is chosen holds nothing that takes the keyboard, so it takes the keyboard itself,
	to be scrolled by its keys -->
<div data-testid={testId} class="cr-ui-pane-columns">
	<div class="cr-scroller cr-ui-pane-columns-list">{@render list()}</div>
	<div class="cr-ui-pane-columns-beside">
		{@render besideHead()}
		<!-- A region that scrolls takes the keyboard to be scrolled by its keys, ringed as all the page's stops are -->
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<div class="cr-ui-pane-columns-beside-body" role="region" aria-label={besideLabel} tabindex="0">
			{@render beside()}
		</div>
	</div>
</div>

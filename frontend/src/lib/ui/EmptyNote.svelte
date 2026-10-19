<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';
	import type { IconName } from './icons';

	/** What it stands in: a list of a pane or a column, at the size of the list's words; or a view of what is read. */
	type Within = 'list' | 'view';

	// The class of each in the library's stylesheet
	const WITHIN: Record<Within, string> = { list: 'cr-ui-empty-in-a-list', view: 'cr-ui-empty-in-a-view' };

	interface Props {
		within: Within;
		/** What stands above its words for what is not there yet, where it stands alone in what it empties. */
		mark?: IconName | undefined;
		testId: string;
		/** What it says: that there is nothing, and why or what will come. */
		children: Snippet;
	}

	let { within, mark, testId, children }: Props = $props();
</script>

<!-- What a list or a view says while it has nothing to show, in muted words with room round them. No rule
	refuses one drawn by hand: muted words with room round them are what no pattern tells from other words -->
<div data-testid={testId} class={['cr-ui-empty', WITHIN[within]]}>
	{#if mark}
		<Icon name={mark} size="xl" tone="absent" />
	{/if}
	<p>{@render children()}</p>
</div>

<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * How what it holds is laid out: one under another at the start of the column — an act on the whole
	 * conversation and why it failed — or across it, a rule either side: where a round ended, what the review did;
	 * or on a line of its own under the turn it is about, on the tint of what cannot be undone: that it was taken
	 * back (TakenBack).
	 */
	type Lays = 'stacked' | 'across' | 'taken-back';

	const LAYS: Record<Lays, string> = {
		stacked: 'cr-ui-turn-aside-stacked',
		across: 'cr-ui-turn-aside-across',
		'taken-back': 'cr-ui-turn-aside-taken-back'
	};

	interface Props {
		lays: Lays;
		testId: string;
		children: Snippet;
	}

	let { lays, testId, children }: Props = $props();
</script>

<!-- A row of a conversation that nobody says: on its spine, in the column of what was said -->
<div data-testid={testId} class={['cr-ui-turn-row cr-ui-turn-aside', LAYS[lays]]}>
	{#if lays === 'across'}
		<span class="cr-ui-turn-aside-rule"></span>
		{@render children()}
		<span class="cr-ui-turn-aside-rule"></span>
	{:else}
		{@render children()}
	{/if}
</div>

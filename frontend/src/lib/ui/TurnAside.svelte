<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * How what it holds is laid out: across the column, a rule either side — where a round ended, what the review
	 * did; on a line of its own under the turn it is about, on the tint of what cannot be undone: that it was
	 * taken back (TakenBack); or standing on the spine, as an avatar does, a rule after it across the rest of the
	 * row: the button that opens earlier turns folded away (TurnsFold).
	 */
	type Lays = 'across' | 'taken-back' | 'on-the-spine';

	const LAYS: Record<Lays, string> = {
		across: 'cr-ui-turn-aside-across',
		'taken-back': 'cr-ui-turn-aside-taken-back',
		'on-the-spine': 'cr-ui-turn-aside-on-the-spine'
	};

	interface Props {
		lays: Lays;
		testId: string;
		children: Snippet;
	}

	let { lays, testId, children }: Props = $props();
</script>

<!-- A row of a conversation that nobody says: on its spine, in the column of what was said or over the spine itself -->
<div data-testid={testId} class={['cr-ui-turn-row', LAYS[lays]]}>
	{#if lays === 'across'}
		<span class="cr-ui-turn-aside-rule"></span>
		{@render children()}
		<span class="cr-ui-turn-aside-rule"></span>
	{:else if lays === 'on-the-spine'}
		{@render children()}
		<span class="cr-ui-turn-aside-rule"></span>
	{:else}
		{@render children()}
	{/if}
</div>

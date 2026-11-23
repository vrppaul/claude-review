<script lang="ts">
	import type { Snippet } from 'svelte';

	/** How what it holds is laid out: across the column between rules, under its turn (TakenBack), or on the spine (TurnsFold). */
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

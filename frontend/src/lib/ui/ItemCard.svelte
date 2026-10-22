<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * What pressing it does: takes the reader to what it lists, which waits for the next round on a dashed edge, on the
	 * reader's wash, and steps back once the agent has it whole; or nothing yet, for a comment still being written,
	 * which is drawn as the card it becomes, on a dashed edge and no ground.
	 */
	type Standing =
		| {
				onclick: () => void;
				/** Whether what it lists waits for the next round, or the agent has it whole. */
				waits: boolean;
		  }
		| { beingWritten: true };

	type Props = Standing & {
		testId: string;
		/** Where what it lists stands: a thread's place, as a chip. */
		place: Snippet;
		/** What stands at the end of its place's line: what a comment asks for, whose it is, the round it went with. */
		trailing?: Snippet | undefined;
		/** What it holds under its place, cut where two lines end: a comment's words. */
		below: Snippet;
	};

	let { testId, place, trailing, below, ...standing }: Props = $props();
</script>

<!-- What either kind holds: its place and what is said of it on one line, its words under it -->
{#snippet held()}
	<span class="cr-ui-item-card-line">
		{@render place()}
		{#if trailing}
			<span class="cr-ui-item-card-end">{@render trailing()}</span>
		{/if}
	</span>
	<span data-testid="{testId}-below" class="cr-ui-item-card-below">{@render below()}</span>
{/snippet}

<!-- An item of a list that holds words, boxed apart as a card of one room, type and height whatever it lists: one
	press to it, or the card a comment still being written becomes -->
{#if 'onclick' in standing}
	<button
		type="button"
		data-testid={testId}
		class={['cr-ui-item-card cr-pressable', standing.waits ? 'cr-ui-item-card-waiting' : 'cr-ui-item-card-sent']}
		onclick={standing.onclick}
	>
		{@render held()}
	</button>
{:else}
	<div data-testid={testId} class="cr-ui-item-card cr-ui-item-card-being-written">
		{@render held()}
	</div>
{/if}

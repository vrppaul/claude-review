<script lang="ts">
	import type { Snippet } from 'svelte';
	import Card from './Card.svelte';
	import EdgeFrame from './EdgeFrame.svelte';
	import { BANDS_BY_FRAME, type FrameLook } from './frame';

	interface Props {
		/** Whether it is the one the reader is at: something of theirs hangs open under it. */
		current: boolean;
		/**
		 * Where its words stand: in a frame of their own, an edge or a card; in none, on the edge of the part they
		 * stand in; or as an item of a list on a card of lists.
		 */
		frame: FrameLook;
		/** The block's test id; its band, its frame and what hangs under it are known by this followed by `-band`, `-frame`, `-hangs`. */
		testId: string;
		/** What it holds: what heads it, and its words. */
		children: Snippet;
		/** What it offers while it is pointed at or holds the keyboard: the act on what it holds. */
		offer: Snippet;
		/** What hangs under it: the threads on it, and a comment being written on it. */
		under?: Snippet | undefined;
	}

	let { current, frame, testId, children, offer, under }: Props = $props();
</script>

<!-- The band, lit across the frame it stands in (lib/ui/frame.ts): from inside an edge frame's edge to its far
	side, past words in no frame either side, the whole of a card, or a pill round an item's words; by the pointer's
	light while pointed at or holding the keyboard, on the reader's mark while it is the one they are at; offering its
	act while lit, over its top right edge, inside a card's top right corner, or in an item's column of its own -->
{#snippet band()}
	<div data-testid="{testId}-band" class={['cr-ui-band', BANDS_BY_FRAME[frame.shape], current && 'cr-ui-band-current']}>
		{@render children()}
		<span class="cr-ui-band-offer">{@render offer()}</span>
	</div>
{/snippet}

<!-- A block the reader may ask about: its band, in a frame of its own where it has one, and what hangs under it
	below that frame, or below its band where it has none -->
<div data-testid={testId}>
	{#if frame.shape === 'edge'}
		<EdgeFrame look={frame} testId="{testId}-frame">
			{@render band()}
		</EdgeFrame>
	{:else if frame.shape === 'card'}
		<Card tone={frame.tone} washed testId="{testId}-frame">
			{@render band()}
		</Card>
	{:else}
		{@render band()}
	{/if}
	{#if under}
		<div data-testid="{testId}-hangs" class="cr-ui-band-under">{@render under()}</div>
	{/if}
</div>

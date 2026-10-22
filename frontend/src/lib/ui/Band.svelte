<script lang="ts">
	import type { Snippet } from 'svelte';
	import Card from './Card.svelte';
	import EdgeFrame from './EdgeFrame.svelte';
	import type { FrameLook } from './frame';

	interface Props {
		/** Whether it is the one the reader is at: something of theirs hangs open under it. */
		current: boolean;
		/** The frame its words stand in where they have one of their own, an edge or a card; none where it shares the frame round it. */
		frame?: FrameLook | undefined;
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
	side, or the whole of a card; by the pointer's light while pointed at or holding the keyboard, on the reader's
	mark while it is the one they are at; offering its act while lit, over its top right edge, or inside a card's
	top right corner -->
{#snippet band()}
	<div
		data-testid="{testId}-band"
		class={['cr-ui-band', frame?.shape === 'card' && 'cr-ui-band-on-a-card', current && 'cr-ui-band-current']}
	>
		{@render children()}
		<span class="cr-ui-band-offer">{@render offer()}</span>
	</div>
{/snippet}

<!-- A block the reader may ask about: its band, in a frame of its own where it has one, and what hangs under it
	below that frame, from where the band ends. A block on a card says so, for the blocks round it to stack as cards -->
<div data-testid={testId} class={[frame?.shape === 'card' && 'cr-ui-band-block-carded']}>
	{#if frame?.shape === 'edge'}
		<EdgeFrame look={frame} testId="{testId}-frame">
			{@render band()}
		</EdgeFrame>
	{:else if frame?.shape === 'card'}
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

<script lang="ts">
	import type { Snippet } from 'svelte';
	import EdgeFrame from './EdgeFrame.svelte';
	import type { FrameLook } from './frame';

	interface Props {
		/** Whether it is the one the reader is at: something of theirs hangs open under it. */
		current: boolean;
		/** The frame its words stand in where they have one of their own; none where it shares the frame round it. */
		frame?: FrameLook | undefined;
		/** The block's test id; its band, its frame and what hangs under it are known by this followed by `-band`, `-frame`, `-hangs`. */
		testId: string;
		/** What it holds: what heads it, and its words. */
		children: Snippet;
		/** What it offers over its top right edge while it is pointed at or holds the keyboard: the act on what it holds. */
		offer: Snippet;
		/** What hangs under it: the threads on it, and a comment being written on it. */
		under?: Snippet | undefined;
	}

	let { current, frame, testId, children, offer, under }: Props = $props();
</script>

<!-- The band, lit across the frame it stands in, from inside the frame's edge to its far side
	(lib/ui/frame.ts): by the pointer's light while pointed at or holding the keyboard, on the reader's mark while
	it is the one they are at; offering its act over its top right edge while lit -->
{#snippet band()}
	<div data-testid="{testId}-band" class={['cr-ui-band', current && 'cr-ui-band-current']}>
		{@render children()}
		<span class="cr-ui-band-offer">{@render offer()}</span>
	</div>
{/snippet}

<!-- A block the reader may ask about: its band, in a frame of its own where it has one, and what hangs under it
	below that frame, from where the band ends -->
<div data-testid={testId}>
	{#if frame}
		<EdgeFrame {...frame} testId="{testId}-frame">
			{@render band()}
		</EdgeFrame>
	{:else}
		{@render band()}
	{/if}
	{#if under}
		<div data-testid="{testId}-hangs" class="cr-ui-band-under">{@render under()}</div>
	{/if}
</div>

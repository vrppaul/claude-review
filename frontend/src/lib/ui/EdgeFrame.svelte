<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import { FRAME_GROUNDS, FRAME_ROOMS, FRAME_TONES, type FrameGround, type FrameHolds, type FrameTone } from './frame';

	interface Props extends Omit<HTMLAttributes<HTMLDivElement>, 'class' | 'style' | 'children'> {
		tone: FrameTone;
		ground: FrameGround;
		/** Its edge broken: words read out of the code, not said by whoever made it. */
		dashed?: boolean | undefined;
		/** Whether it holds words, or the bands of blocks the reader may ask about, which take its room inside them. */
		holds?: FrameHolds | undefined;
		testId: string;
		children: Snippet;
	}

	let { tone, ground, dashed = false, holds = 'words', testId, children, ...attributes }: Props = $props();
</script>

<!-- Words set apart by a line down their start, in the colour of whose or what they are (lib/ui/frame.ts) -->
<div
	{...attributes}
	data-testid={testId}
	class={[
		'cr-ui-edge-frame',
		FRAME_TONES[tone],
		FRAME_GROUNDS[ground],
		FRAME_ROOMS[holds],
		dashed && 'cr-ui-frame-dashed'
	]}
>
	{@render children()}
</div>

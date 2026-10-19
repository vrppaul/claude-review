<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import { FRAME_GROUNDS, FRAME_TONES, type FrameGround, type FrameTone } from './frame';

	interface Props extends Omit<HTMLAttributes<HTMLDivElement>, 'class' | 'style' | 'children'> {
		tone: FrameTone;
		ground: FrameGround;
		/** Its edge broken: words read out of the code, not said by whoever made it. */
		dashed?: boolean | undefined;
		testId: string;
		children: Snippet;
	}

	let { tone, ground, dashed = false, testId, children, ...attributes }: Props = $props();
</script>

<!-- Words set apart by a line down their start, in the colour of whose or what they are (lib/ui/frame.ts) -->
<div
	{...attributes}
	data-testid={testId}
	class={['cr-ui-edge-frame', FRAME_TONES[tone], FRAME_GROUNDS[ground], dashed && 'cr-ui-frame-dashed']}
>
	{@render children()}
</div>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import { type EdgeLook, FRAME_GROUNDS, FRAME_TONES } from './frame';

	interface Props {
		/** Whose its words are, and whether it lays their colour's ground. */
		look: EdgeLook;
		testId: string;
		children: Snippet;
	}

	let { look, testId, children }: Props = $props();
</script>

<!-- Words set apart by a line down their start, in the colour of whose or what they are (lib/ui/frame.ts) -->
<div data-testid={testId} class={['cr-ui-edge-frame', FRAME_TONES[look.tone], FRAME_GROUNDS[look.ground]]}>
	{@render children()}
</div>

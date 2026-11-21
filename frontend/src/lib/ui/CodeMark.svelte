<script lang="ts">
	import { untrack } from 'svelte';
	import type { CodeMark, CodeMarks } from '$lib/dom/code-marks';
	import { EveryFrame } from '$lib/dom/every-frame';
	import type { AreaBox } from '$lib/dom/scroll-area';
	import { EDGED, edgeBoxes, sameEdge } from './code-mark';
	import { pixels } from './pane';

	interface Props {
		/** The stretch of the code marked, as it is drawn now: none while it is not drawn. */
		stretch: () => Range | null;
		/** What the mark says of the words under it. */
		mark: CodeMark;
		/** The page's marks over the code, which this one is laid on while it is drawn. */
		marks: CodeMarks;
		testId: string;
	}

	let { stretch, mark, marks, testId }: Props = $props();

	// The layer its edge is drawn on, and the edge's boxes as the stretch stood when last read
	let layer = $state<HTMLElement>();
	let boxes = $state.raw<AreaBox[]>([]);
	// The stretch its ground is laid on now
	let laid: Range | null = null;

	// It follows the stretch, read each frame while the mark is drawn: the line it is on is drawn again as what the
	// page shows changes, wraps as the window narrows, and is pushed down by what grows above it with nothing
	// scrolled or resized. As it goes, its ground comes off the stretch it was last laid on
	$effect(() => {
		untrack(follow);
		const following = new EveryFrame(follow);
		return () => leave(following);
	});

	/** The mark goes: it follows nothing more, and its ground comes off. */
	function leave(following: EveryFrame) {
		following.stop();
		layOn(null);
	}

	/** Lay the ground on the stretch as it is drawn now, and move the edge to where it stands. */
	function follow() {
		const drawn = stretch();
		layOn(drawn);
		if (!layer) return;
		const read = drawn === null ? [] : edgeBoxes(drawn, layer);
		if (!sameEdge(read, boxes)) boxes = read;
	}

	/** Move the ground to a stretch, off the one it lay on: to none, once the stretch is not drawn. */
	function layOn(drawn: Range | null) {
		if (drawn === laid) return;
		if (laid !== null) marks.takeOff(mark, laid);
		if (drawn !== null) marks.lay(mark, drawn);
		laid = drawn;
	}
</script>

<!-- A layer over the code it is drawn in, letting every press through, its words read, pressed and picked out as on
	any line; a box round each line of the stretch -->
{#if EDGED[mark]}
	<span bind:this={layer} data-testid={testId} class="cr-ui-code-mark-edges">
		{#each boxes as box, line (line)}
			<span
				class="cr-ui-code-mark-edge"
				style:--cr-edge-left={pixels(box.left)}
				style:--cr-edge-top={pixels(box.top)}
				style:--cr-edge-width={pixels(box.width)}
				style:--cr-edge-height={pixels(box.height)}
			></span>
		{/each}
	</span>
{/if}

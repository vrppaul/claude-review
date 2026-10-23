<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * How tall it stands:
	 * - xs: a setting in a pane, a file's way of being shown on its bar, what a comment asks for: its words small
	 * - sm: among the header's controls, as tall as they are (a small button's height)
	 */
	type SegmentedSize = 'xs' | 'sm';

	// The class of each in the library's stylesheet, over the track every size has
	const SIZES: Record<SegmentedSize, string | null> = { xs: null, sm: 'cr-ui-segmented-sm' };

	interface Props {
		/** What its segments pick between, said to whoever cannot see them. */
		label: string;
		size: SegmentedSize;
		testId: string;
		/** The name the tour lights it by, where the tour stops at it, written with lib/guide/tour.ts's tourStop. */
		'data-tour'?: string | undefined;
		/** Its segments, each a `Segment`. */
		children: Snippet;
	}

	let { label, size, testId, 'data-tour': tour, children }: Props = $props();
</script>

<!-- A track of segments, the one picked marked on it: what is picked here is a way of reading, not an act -->
<div data-testid={testId} data-tour={tour} class={['cr-ui-segmented', SIZES[size]]} role="group" aria-label={label}>
	{@render children()}
</div>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import { arrowOffsetTo, type PaneEdge, type Placement } from './pane';
	import PopoverPanel from './PopoverPanel.svelte';

	interface Props {
		/** The control the note stands under, which the keyboard goes back to as the note goes. */
		pointsAt: HTMLElement | undefined;
		/** What the note is called, said to whoever cannot see it. */
		label: string;
		/** Which of the control's edges it lines up with, as a pane opened from there would. */
		placement: Placement;
		/** Whether it points at the control: a note that is not about it does not. */
		arrow: boolean;
		/** What it says by its edge, where it says anything by it. */
		edge?: PaneEdge | undefined;
		/** Whether it fades as its time runs out; one that does not shows the time left itself. */
		fades: boolean;
		testId: string;
		/** Called once the note goes, by itself or as it is put away, for whoever drew it to stop drawing it. */
		onGone: () => void;
		/** What the note says and offers, handed the way to put it away at once. */
		children: Snippet<[putAway: () => void]>;
	}

	// How long a note stands before it puts itself away, the mouse over it or not. Whatever shows the time
	// running out reads it as --cr-note-lasts; the note goes by this clock, not by what shows it, which
	// runs for no reader who asked for less motion
	const STANDS_FOR_MS = 4_000;

	let { pointsAt, label, placement, arrow, edge, fades, testId, onGone, children }: Props = $props();

	let pane: HTMLDivElement | undefined = $state();
	// How far in from its left edge the note points at the control, where it draws an arrow
	const arrowOffset = $derived(arrowOffsetTo(pointsAt));

	// Started as the note is drawn, and let go with it: put away before, it puts nothing away
	$effect(() => {
		const timer = setTimeout(putAway, STANDS_FOR_MS);
		return () => clearTimeout(timer);
	});

	/** Put the note away. The keyboard it held, if it held it, goes to the control it stands under. */
	function putAway() {
		if (pane?.contains(document.activeElement)) focusWhatRemains(() => pointsAt);
		onGone();
	}
</script>

<!-- Said under a control by the page, of something that happened: a note, and no popover, for it opens from no
	control and takes the keyboard from nothing the reader is doing. It lies over what is under it, so it goes
	by itself in a few seconds, or at once as it is put away -->
<div class="contents" style:--cr-note-lasts="{STANDS_FOR_MS}ms">
	<PopoverPanel
		bind:pane
		role="status"
		{label}
		{placement}
		width="fitted"
		{arrow}
		{arrowOffset}
		{edge}
		fading={fades}
		{testId}
	>
		{@render children(putAway)}
	</PopoverPanel>
</div>

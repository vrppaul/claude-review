<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import { useReview } from '$lib/review/context';
	import { arrowOffsetTo } from './pane-placement';
	import PopoverPanel from './PopoverPanel.svelte';
	import { chaptersIn } from './story-words';

	interface Props {
		/** The control that leads to the story, which the note stands under and points at. */
		pointsAt: HTMLElement | undefined;
		/** What opening the story does: how the review is read is its to change who draws the note. */
		onOpen: () => void;
	}

	// How long the note stands before it puts itself away, the mouse over it or not. The bar along its foot
	// runs out over as long; the note goes by this clock, not by the bar, which runs for no reader who asked
	// for less motion
	const STANDS_FOR_MS = 4_000;

	let { pointsAt, onOpen }: Props = $props();
	const review = useReview();

	let pane: HTMLDivElement | undefined = $state();
	// How far in from its left edge the note points at the control
	const arrowOffset = $derived(pointsAt ? arrowOffsetTo(pointsAt) : 0);
	// How far from the left of the window the note stands, as it is drawn: where the box it is placed in
	// begins. It is no wider than the window has room for from there, so on a narrow screen its words
	// wrap, and nothing of it is cut off
	const standsAt = $derived(pane?.offsetParent?.getBoundingClientRect().left ?? 0);

	// Started as the note is drawn, and let go with it: opened or closed before, it puts nothing away
	$effect(() => {
		const timer = setTimeout(putAway, STANDS_FOR_MS);
		return () => clearTimeout(timer);
	});

	/** Put the note away. The keyboard it held, if it held it, goes to the control it pointed at. */
	function putAway() {
		if (pane?.contains(document.activeElement)) focusWhatRemains(() => pointsAt);
		review.story.putOfferAway();
	}
</script>

<!-- Said under the control that leads to a story, once one told while the reader read the files has arrived.
	A note, and no popover: it opens from no control, and takes the keyboard from nothing the reader is
	doing. It lies over what is under it, so it goes by itself in a few seconds, or at once by its ×; the
	view is the reader's to change -->
<div class="contents" style:--cr-note-stands-at="{standsAt}px">
	<PopoverPanel
		bind:pane
		role="status"
		label="The story is ready"
		placement="below-start"
		{arrowOffset}
		data-testid="story-ready"
		class="cr-popover-note cr-popover-unread"
	>
		<div class="flex flex-wrap items-center gap-x-3 gap-y-2 py-2 pr-2 pl-3.5 text-sm">
			<span>The story is ready: {chaptersIn(review.story.contents.chapters.length)}.</span>
			<button type="button" data-testid="open-story" class="btn btn-primary btn-xs" onclick={onOpen}>Open it</button>
			<button
				type="button"
				data-testid="story-ready-close"
				class="btn btn-ghost btn-xs"
				aria-label="Close"
				onclick={putAway}>×</button
			>
		</div>
		<div
			data-testid="story-ready-time-left"
			class="cr-note-time-left"
			style:--cr-note-lasts="{STANDS_FOR_MS}ms"
			aria-hidden="true"
		></div>
	</PopoverPanel>
</div>

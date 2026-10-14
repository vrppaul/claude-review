<script lang="ts">
	import { focusWhatRemains, isComposingText, isTypingTarget } from '$lib/dom/keyboard';
	import { inModalAbove } from '$lib/dom/modal';
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

	// The key that puts the note away
	const PUT_AWAY_KEY = 'Escape';

	let { pointsAt, onOpen }: Props = $props();
	const review = useReview();

	let pane: HTMLDivElement | undefined = $state();
	// How far in from its left edge the note points at the control
	const arrowOffset = $derived(pointsAt ? arrowOffsetTo(pointsAt) : 0);
	// How far from the left of the window the note stands, as it is drawn: where the box it is placed in
	// begins. It is no wider than the window has room for from there, so on a narrow screen its words
	// wrap, and nothing of it is cut off
	const standsAt = $derived(pane?.offsetParent?.getBoundingClientRect().left ?? 0);

	/** Put the note away. The keyboard it held, if it held it, goes to the control it pointed at. */
	function putAway() {
		if (pane?.contains(document.activeElement)) focusWhatRemains(() => pointsAt);
		review.story.putOfferAway();
	}

	/** Escape puts it away, unless the key is a field's, part of a word being composed, or a modal's above it. */
	function putAwayOnEscape(event: KeyboardEvent) {
		if (event.key !== PUT_AWAY_KEY || isComposingText(event)) return;
		if (isTypingTarget(event.target) || inModalAbove(event.target)) return;
		putAway();
	}

	/** A press anywhere else on the page puts it away, and does what it would have done anyway. */
	function putAwayIfPressedElsewhere(event: PointerEvent) {
		if (!(event.target instanceof Node) || pane?.contains(event.target) || inModalAbove(event.target)) return;
		putAway();
	}
</script>

<svelte:document onpointerdown={putAwayIfPressedElsewhere} />
<svelte:window onkeydown={putAwayOnEscape} />

<!-- Said under the control that leads to a story, once one told while the reader read the files has arrived.
	A note, and no popover: it opens from no control, and takes the keyboard from nothing the reader is
	doing. It lies over what is under it, so Escape or a press elsewhere puts it away; the view is the
	reader's to change -->
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
		</div>
	</PopoverPanel>
</div>

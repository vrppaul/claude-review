<script lang="ts">
	import { tick, type Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import { clippingRound, seenIn } from '$lib/dom/in-sight';
	import PaneHead from './PaneHead.svelte';
	import {
		fitted,
		laidOut,
		PANE_EDGES,
		PANE_WIDTHS,
		pixels,
		placedAs,
		type PaneEdge,
		type PaneFit,
		type PaneHead as Head,
		type PaneWidth,
		type Placement,
		type Way
	} from './pane';

	interface Props extends Omit<HTMLAttributes<HTMLDivElement>, 'class' | 'style' | 'children' | 'role' | 'aria-label'> {
		/** What the pane is to a screen reader: a pane of controls, a list to pick from, or a note of something that happened. */
		role: 'dialog' | 'listbox' | 'status';
		/** What the pane is called, said to whoever cannot see it. */
		label: string;
		/** Where it opens, unless it would not stand whole there and the other way has more room. */
		placement: Placement;
		width: PaneWidth;
		/** Whether it points at what it stands by: a note that is not about that control does not. */
		arrow: boolean;
		/** How far from the edge it lines up with the arrow points, in pixels: the middle of what opened it. */
		arrowOffset: number;
		edge?: PaneEdge | undefined;
		/** Whether it fades out over the time a note stands, which whoever puts it there sets as --cr-note-lasts. */
		fading?: boolean;
		/** Whether it comes from the control the reader pressed; a note the page puts there by itself never moves in. */
		comesIn?: boolean;
		head?: Head | undefined;
		/**
		 * Move what it stands by to where that stands now, before each fit: for a pane by a stretch of text, which
		 * no control holds and which moves as its line wraps.
		 */
		place?: (() => void) | undefined;
		/**
		 * Whether it is drawn at a spot inside what scrolls, and scrolls with it as a card in the code does, fitted
		 * again only as what it is seen in changes size; any other pane is fitted again as anything under it scrolls.
		 */
		scrollsWithItsSpot?: boolean;
		testId: string;
		/** The pane itself, held by whoever opened it: focus is moved into it and back. */
		pane?: HTMLDivElement | undefined;
		/** What it holds, scrolling inside it, held by whoever opened it to give the keyboard to the first of it. */
		body?: HTMLDivElement | undefined;
		children: Snippet;
		/** What stays at its foot while what it holds scrolls: the act it leads to, or what it asks of the reader. */
		foot?: Snippet | undefined;
		/** Whether its foot asks something of the reader, standing apart from the pane on the page's plainest ground. */
		footAsks?: boolean;
	}

	let {
		role,
		label,
		placement,
		width,
		arrow,
		arrowOffset,
		edge,
		fading = false,
		comesIn = false,
		head,
		place,
		scrollsWithItsSpot = false,
		testId,
		pane = $bindable(),
		body = $bindable(),
		children,
		foot,
		footAsks = false,
		...attributes
	}: Props = $props();

	// How the pane is fitted into what it is seen in, once it is drawn
	let fit = $state<PaneFit | null>(null);
	// The way it opened at its last fit, handed to the next: a placement that chooses as the pane opens keeps it
	let opened: Way | null = null;

	// Measured as it is drawn, and whenever what it is seen in changes under it
	$effect(() => {
		if (pane && body) void measure();
	});

	// And as any box it is seen in changes size, the window as it was: a side column opened or put away beside the
	// reading area the pane stands in
	$effect(() => {
		if (!pane) return;
		const seenInChanging = new ResizeObserver(() => void measure());
		for (const box of clippingRound(pane)) seenInChanging.observe(box);
		return () => seenInChanging.disconnect();
	});

	/**
	 * Fit the pane into what of the window it is seen in where it is drawn: the window, or the part of a reading
	 * area not under what is kept in sight at its top (dom/in-sight.ts). What it stands by is moved first to where
	 * it stands now, where whoever drew the pane places it, and the fit waits for that to be drawn.
	 */
	async function measure() {
		if (place) {
			place();
			await tick();
		}
		if (!pane || !body) return;
		const fitNow = fitted(laidOut(pane, body), placement, seenIn(pane), opened);
		fit = fitNow;
		opened = fitNow.placement;
	}

	/** Something under the pane scrolled: it is fitted again, unless it scrolls with the spot it stands by. */
	function noteScroll() {
		if (!scrollsWithItsSpot) void measure();
	}
</script>

<!-- What the pane is seen in, and the place of what it stands by, change as the window is resized and as anything
	under the pane scrolls: the pane is fitted to them again -->
<svelte:window onresize={() => void measure()} onscrollcapture={noteScroll} />

<!-- One look for every pane that stands by a control, opened from it by the reader or put there by the page as a
	note: lifted off the page, with an arrow pointing at the control, opened the way it has room and moved in to
	stand whole in what it is seen in -->
<div
	{...attributes}
	bind:this={pane}
	{role}
	aria-label={label}
	data-testid={testId}
	class={[
		'cr-ui-pane cr-ui-popover',
		placedAs(fit?.placement ?? placement),
		PANE_WIDTHS[width],
		edge && PANE_EDGES[edge],
		!arrow && 'cr-ui-arrowless',
		fading && 'cr-ui-pane-fading',
		comesIn && 'cr-ui-pane-coming'
	]}
	style:--cr-arrow-offset="{arrowOffset}px"
	style:--cr-pane-shift={pixels(fit?.shift)}
	style:--cr-pane-most-width={pixels(fit?.mostWidth)}
	style:--cr-pane-most-height={pixels(fit?.mostHeight)}
>
	<!-- Over the arrow's inner half, and round at the pane's corners, so nothing lit inside it shows past them -->
	<div class="cr-ui-pane-inside">
		{#if head}
			<PaneHead {head} {testId} />
		{/if}
		<div bind:this={body} class="cr-scroller cr-ui-pane-body">
			{@render children()}
		</div>
		{#if foot}
			<div class={['cr-ui-pane-foot', footAsks && 'cr-ui-pane-foot-asking']}>{@render foot()}</div>
		{/if}
	</div>
</div>

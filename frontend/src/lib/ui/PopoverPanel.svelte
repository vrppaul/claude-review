<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import PaneHead from './PaneHead.svelte';
	import {
		fitted,
		laidOut,
		PANE_EDGES,
		PANE_WIDTHS,
		placedAs,
		type PaneEdge,
		type PaneFit,
		type PaneHead as Head,
		type PaneWidth,
		type Placement,
		type ScreenBox
	} from './pane';

	interface Props extends Omit<HTMLAttributes<HTMLDivElement>, 'class' | 'style' | 'children' | 'role' | 'aria-label'> {
		/** What the pane is to a screen reader: a pane of controls, a list to pick from, or a note of something that happened. */
		role: 'dialog' | 'listbox' | 'status';
		/** What the pane is called, said to whoever cannot see it. */
		label: string;
		/** Where it opens, unless it would not stand whole there and the other way has more room. */
		placement: Placement;
		/**
		 * What of the window the pane can be seen in where it is drawn, asked each time it is fitted: the window, or
		 * the part of a reading area not under what is kept in sight at its top (dom/in-sight.ts).
		 */
		seenIn: (pane: HTMLElement) => ScreenBox;
		width: PaneWidth;
		/** Whether it points at what it stands by: a note that is not about that control does not. */
		arrow: boolean;
		/** How far from the edge it lines up with the arrow points, in pixels: the middle of what opened it. */
		arrowOffset: number;
		edge?: PaneEdge | undefined;
		/** Whether it fades out over the time a note stands, which whoever puts it there sets as --cr-note-lasts. */
		fading?: boolean;
		head?: Head | undefined;
		testId: string;
		/** The pane itself, held by whoever opened it: focus is moved into it and back. */
		pane?: HTMLDivElement | undefined;
		/** What it holds, scrolling inside it, held by whoever opened it to give the keyboard to the first of it. */
		body?: HTMLDivElement | undefined;
		children: Snippet;
		/** What stays at its foot while what it holds scrolls: the act it leads to. */
		foot?: Snippet | undefined;
	}

	let {
		role,
		label,
		placement,
		seenIn,
		width,
		arrow,
		arrowOffset,
		edge,
		fading = false,
		head,
		testId,
		pane = $bindable(),
		body = $bindable(),
		children,
		foot,
		...attributes
	}: Props = $props();

	// How the pane is fitted into what it is seen in, once it is drawn
	let fit = $state<PaneFit | null>(null);

	// Measured as it is drawn, and whenever what it is seen in changes under it
	$effect(() => {
		if (pane && body) measure();
	});

	function measure() {
		if (pane && body) fit = fitted(laidOut(pane, body), placement, seenIn(pane));
	}

	/** A number of pixels as the stylesheet takes it, or none before the pane is measured. */
	function pixels(measured: number | undefined): string | undefined {
		return measured === undefined ? undefined : `${measured}px`;
	}
</script>

<!-- What the pane is seen in, and the place of what it stands by, change as the window is resized and as anything
	under the pane scrolls: the pane is fitted to them again -->
<svelte:window onresize={measure} onscrollcapture={measure} />

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
		fading && 'cr-ui-pane-fading'
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
			<div class="cr-ui-pane-foot">{@render foot()}</div>
		{/if}
	</div>
</div>

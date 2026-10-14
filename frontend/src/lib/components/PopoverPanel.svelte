<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import type { Placement } from './pane-placement';

	interface Props extends HTMLAttributes<HTMLDivElement> {
		/** What the pane is to a screen reader: a pane of controls, a list to pick from, or a note of something that happened. */
		role: 'dialog' | 'listbox' | 'status';
		/** What the pane is called, said to whoever cannot see it. */
		label: string;
		placement: Placement;
		/** How far from the edge it lines up with the arrow points, in pixels: the middle of what opened it. */
		arrowOffset: number;
		/** The pane itself, held by whoever opened it: focus is moved into it and back. */
		pane?: HTMLDivElement | undefined;
		children: Snippet;
	}

	let { role, label, placement, arrowOffset, pane = $bindable(), children, class: sized, ...marked }: Props = $props();

	// How far from the left of the window the pane stands, as it is drawn: where the box it is placed in
	// begins. A pane the page puts by a control as a note is no wider than the window has room for from
	// there, so on a narrow screen its words wrap, and nothing of it is cut off
	const standsAt = $derived(pane?.offsetParent?.getBoundingClientRect().left ?? 0);
</script>

<!-- One look for every pane that stands by a control, opened from it by the reader or put there by the page as a
	note: lifted off the page, with an arrow pointing at the control -->
<div
	{...marked}
	bind:this={pane}
	{role}
	aria-label={label}
	class={['cr-popover', `cr-popover-${placement}`, sized]}
	style:--cr-arrow-offset="{arrowOffset}px"
	style:--cr-pane-stands-at="{standsAt}px"
>
	<div class="cr-popover-body">
		{@render children()}
	</div>
</div>

<script lang="ts" module>
	/** Where a pane opens beside what opened it, and which of its edges it lines up with. */
	export type Placement = 'below-start' | 'below-end' | 'above-start';
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';

	interface Props extends HTMLAttributes<HTMLDivElement> {
		/** What the pane is to a screen reader: a pane of controls, or a list to pick from. */
		role: 'dialog' | 'listbox';
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
</script>

<!-- One look for every pane the reader opens from a control: lifted off the page, with an arrow pointing at the control -->
<div
	{...marked}
	bind:this={pane}
	{role}
	aria-label={label}
	class={['cr-popover', `cr-popover-${placement}`, sized]}
	style:--cr-arrow-offset="{arrowOffset}px"
>
	<div class="cr-popover-body">
		{@render children()}
	</div>
</div>

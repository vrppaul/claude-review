<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ColumnWidth } from '$lib/dom/resize';
	import { COLUMN_SIDES, type ColumnSide } from './column';
	import EdgeGrip from './EdgeGrip.svelte';

	interface Props {
		side: ColumnSide;
		/** How wide it is, between what bounds, and how its grip makes it another width. */
		width: ColumnWidth;
		/** What it is to whoever goes through the page by its parts: something beside what is read, or a way through it. */
		landmark: 'aside' | 'nav';
		/** What that part of the page is called: "Files". */
		label: string;
		/** What its grip resizes, said to whoever cannot see it: "Resize the file tree". */
		resizing: string;
		/** What the tests know the column and its grip by. */
		testIds: { column: string; resize: string };
		/** The name the tour lights it by, where the tour stops at it, written with lib/guide/tour.ts's tourStop. */
		'data-tour'?: string | undefined;
		/** The column itself, for whoever hands the keyboard to what is in it. */
		element?: HTMLElement | undefined;
		children: Snippet;
		/** What stands at its foot, ruled off from what is above it: what the reader writes there. */
		foot?: Snippet | undefined;
	}

	let {
		side,
		width,
		landmark,
		label,
		resizing,
		testIds,
		'data-tour': tour,
		element = $bindable(),
		children,
		foot
	}: Props = $props();

	const drawn = $derived(COLUMN_SIDES[side]);
</script>

<!-- A column beside what is read, as wide as the reader left it and no narrower than it reads at, with the grip
	that sizes it on the edge facing what is read (lib/ui/column.ts) -->
<svelte:element
	this={landmark}
	bind:this={element}
	data-testid={testIds.column}
	data-tour={tour}
	aria-label={label}
	class={['cr-ui-column', drawn.drawnAs]}
	style:--cr-column-width="{width.width}px"
>
	<EdgeGrip column={width} grows={drawn.grows} label={resizing} testId={testIds.resize} />
	{@render children()}
	{#if foot}
		<div class="cr-ui-column-foot">{@render foot()}</div>
	{/if}
</svelte:element>

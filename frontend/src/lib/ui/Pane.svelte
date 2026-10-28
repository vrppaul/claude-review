<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import PaneHead from './PaneHead.svelte';
	import { PANE_WIDTHS, type PaneHead as Head, type PaneWidth } from './pane';

	interface Props extends Omit<HTMLAttributes<HTMLElement>, 'class' | 'style' | 'children'> {
		width: PaneWidth;
		/** What heads it, as every pane with a head is headed; none for one whose way out stands in what it holds. */
		head?: Head | undefined;
		testId: string;
		children: Snippet;
	}

	let { width, head, testId, children, ...attributes }: Props = $props();
</script>

<!-- A pane that stands by itself, where whoever draws it places it: the look of every pane, with nothing of a
	control's or a modal's, headed as every pane is where it has a head, and kept inside the window, what it holds
	scrolling under its head -->
<section {...attributes} data-testid={testId} class={['cr-ui-pane cr-ui-pane-standing', PANE_WIDTHS[width]]}>
	{#if head}
		<PaneHead {head} {testId} />
	{/if}
	<div class="cr-scroller cr-ui-pane-body">
		{@render children()}
	</div>
</section>

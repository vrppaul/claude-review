<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import { PANE_WIDTHS, type PaneWidth } from './pane';

	interface Props extends Omit<HTMLAttributes<HTMLElement>, 'class' | 'style' | 'children'> {
		width: PaneWidth;
		testId: string;
		children: Snippet;
	}

	let { width, testId, children, ...attributes }: Props = $props();
</script>

<!-- A pane that stands by itself, where whoever draws it places it: the look of every pane, with nothing of a
	control's or a modal's -->
<section {...attributes} data-testid={testId} class={['cr-ui-pane', PANE_WIDTHS[width]]}>
	{@render children()}
</section>

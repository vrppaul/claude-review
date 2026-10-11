<script lang="ts">
	import type { DiffFile } from '$lib/types';
	import { assembleText } from '$lib/utils/renderable';
	import { useReview } from '$lib/review/context';
	import type { FileDrawing } from './file-drawing.svelte';
	import MarkdownRenderer from './MarkdownRenderer.svelte';
	import RawView from './RawView.svelte';

	interface Props {
		file: DiffFile;
		/** Its lines made ready to draw, by whoever draws it. */
		drawing: FileDrawing;
	}

	let { file, drawing }: Props = $props();
	const review = useReview();

	const renderedText = $derived(assembleText(file, review.mode));

	let leftPane: HTMLDivElement | undefined = $state();
	let rightPane: HTMLDivElement | undefined = $state();
	let scrollSource: 'left' | 'right' | null = null;

	function syncScroll(source: 'left' | 'right') {
		// Ignore scroll events triggered by our own assignments
		if (scrollSource !== null && scrollSource !== source) return;
		scrollSource = source;

		const from = source === 'left' ? leftPane : rightPane;
		const to = source === 'left' ? rightPane : leftPane;
		if (!from || !to) return;

		const ratio = from.scrollTop / (from.scrollHeight - from.clientHeight || 1);
		to.scrollTop = ratio * (to.scrollHeight - to.clientHeight);

		// Clear after the browser processes the resulting scroll event
		requestAnimationFrame(() => (scrollSource = null));
	}
</script>

<div data-testid="side-by-side-view" class="flex min-h-0 flex-1">
	<div bind:this={leftPane} class="w-1/2 overflow-auto border-r border-base-300" onscroll={() => syncScroll('left')}>
		<RawView {drawing} />
	</div>
	<div bind:this={rightPane} class="w-1/2 overflow-auto p-4" onscroll={() => syncScroll('right')}>
		<MarkdownRenderer text={renderedText} />
	</div>
</div>

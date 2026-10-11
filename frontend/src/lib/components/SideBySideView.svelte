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
</script>

<!-- The text and what it renders to, half the width each. Neither half
	scrolls up and down on its own: both are as tall as what they hold, and
	the review scrolls them together. A rendered table wider than its half
	scrolls across inside it. -->
<div data-testid="side-by-side-view" class="flex">
	<div class="w-1/2 min-w-0 border-r border-base-300">
		<RawView {drawing} />
	</div>
	<div class="w-1/2 min-w-0 overflow-x-auto p-4">
		<MarkdownRenderer text={renderedText} />
	</div>
</div>

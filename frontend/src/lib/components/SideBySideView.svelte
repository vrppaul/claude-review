<script lang="ts">
	import type { DiffFile } from '$lib/types';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { assembleText } from '$lib/utils/renderable';
	import MarkdownRenderer from './MarkdownRenderer.svelte';
	import RawView from './RawView.svelte';

	interface Props {
		file: DiffFile;
		language: string | null;
	}

	let { file, language }: Props = $props();

	const isDiffMode = $derived(diffStore.mode === 'diff');
	const renderedText = $derived(assembleText(file, isDiffMode));

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
		requestAnimationFrame(() => {
			scrollSource = null;
		});
	}
</script>

<div data-testid="side-by-side-view" class="flex min-h-0 flex-1">
	<div
		bind:this={leftPane}
		class="w-1/2 overflow-auto border-r border-base-300"
		onscroll={() => syncScroll('left')}
	>
		<RawView {file} {language} />
	</div>
	<div
		bind:this={rightPane}
		class="w-1/2 overflow-auto p-4"
		onscroll={() => syncScroll('right')}
	>
		<MarkdownRenderer text={renderedText} />
	</div>
</div>

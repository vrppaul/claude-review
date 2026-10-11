<script lang="ts">
	import type { DiffFile } from '$lib/types';
	import { assembleText } from '$lib/utils/renderable';
	import { counted } from '$lib/utils/words';
	import { useReview } from '$lib/review/context';
	import MarkdownRenderer from './MarkdownRenderer.svelte';

	interface Props {
		file: DiffFile;
	}

	let { file }: Props = $props();
	const review = useReview();

	const fullText = $derived(assembleText(file, review.mode));
	const commentCount = $derived(review.threads.onFile(file.path).length);
	// One piece of text: split across lines, the count and its word would read apart
	const commentNote = $derived(`${counted(commentCount, 'comment', 'comments')} — switch to Raw to view`);
</script>

<div data-testid="preview-view" class="p-4">
	{#if commentCount > 0}
		<div data-testid="preview-comment-badge" class="mb-3">
			<span class="badge badge-warning badge-sm">
				{commentNote}
			</span>
		</div>
	{/if}

	<MarkdownRenderer text={fullText} />
</div>

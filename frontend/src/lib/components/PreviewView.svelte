<script lang="ts">
	import type { DiffFile } from '$lib/types';
	import { assembleText } from '$lib/utils/renderable';
	import { COMMENTS, counted } from '$lib/utils/words';
	import { useReview } from '$lib/review/context';
	import Tag from '$lib/ui/Tag.svelte';
	import MarkdownRenderer from './MarkdownRenderer.svelte';

	interface Props {
		file: DiffFile;
	}

	let { file }: Props = $props();
	const review = useReview();

	const fullText = $derived(assembleText(file, review.mode));
	const commentCount = $derived(review.threads.onLinesOf(file.path).length);
	// One piece of text: split across lines, the count and its word would read apart
	const commentNote = $derived(`${counted(commentCount, COMMENTS)} — switch to Raw to view`);
</script>

<div data-testid="preview-view" class="p-4">
	{#if commentCount > 0}
		<!-- A warning: the threads on this file are not drawn in its preview -->
		<div class="mb-3">
			<Tag tone="warning" testId="preview-comment-badge">{commentNote}</Tag>
		</div>
	{/if}

	<MarkdownRenderer text={fullText} />
</div>

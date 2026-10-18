<script lang="ts">
	import type { ContentViewMode } from '$lib/reader/page-layout.svelte';
	import { useReview } from '$lib/review/context';
	import Segment from '$lib/ui/Segment.svelte';
	import Segmented from '$lib/ui/Segmented.svelte';

	const review = useReview();

	const modes: { value: ContentViewMode; label: string; testId: string }[] = [
		{ value: 'raw', label: 'Raw', testId: 'view-mode-raw' },
		{ value: 'preview', label: 'Preview', testId: 'view-mode-preview' },
		{ value: 'side-by-side', label: 'Both', testId: 'view-mode-side-by-side' }
	];
</script>

<Segmented label="How to show this file" testId="content-view-toggle">
	{#each modes as mode (mode.value)}
		<Segment
			testId={mode.testId}
			pressed={review.layout.contentView.mode === mode.value}
			onclick={() => review.layout.contentView.set(mode.value)}
		>
			{mode.label}
		</Segment>
	{/each}
</Segmented>

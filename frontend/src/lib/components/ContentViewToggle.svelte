<script lang="ts">
	import type { ContentViewMode } from '$lib/reader/page-layout.svelte';
	import { useReview } from '$lib/review/context';

	const review = useReview();

	const modes: { value: ContentViewMode; label: string; testId: string }[] = [
		{ value: 'raw', label: 'Raw', testId: 'view-mode-raw' },
		{ value: 'preview', label: 'Preview', testId: 'view-mode-preview' },
		{ value: 'side-by-side', label: 'Both', testId: 'view-mode-side-by-side' }
	];
</script>

<div data-testid="content-view-toggle" class="cr-segmented">
	{#each modes as mode (mode.value)}
		<button
			type="button"
			data-testid={mode.testId}
			class="cr-segment"
			aria-pressed={review.layout.contentView.mode === mode.value}
			onclick={() => review.layout.contentView.set(mode.value)}
		>
			{mode.label}
		</button>
	{/each}
</div>

<script lang="ts">
	import type { ContentViewMode } from '$lib/types';
	import { diffStore } from '$lib/stores/diff.svelte';

	const modes: { value: ContentViewMode; label: string; testId: string }[] = [
		{ value: 'raw', label: 'Raw', testId: 'view-mode-raw' },
		{ value: 'preview', label: 'Preview', testId: 'view-mode-preview' },
		{ value: 'side-by-side', label: 'Side by side', testId: 'view-mode-side-by-side' }
	];
</script>

<div data-testid="content-view-toggle" class="join ml-4">
	{#each modes as mode (mode.value)}
		<button
			data-testid={mode.testId}
			class="join-item btn btn-xs {diffStore.contentViewMode === mode.value ? 'btn-primary' : 'btn-outline btn-primary'}"
			onclick={() => diffStore.setContentViewMode(mode.value)}
		>
			{mode.label}
		</button>
	{/each}
</div>

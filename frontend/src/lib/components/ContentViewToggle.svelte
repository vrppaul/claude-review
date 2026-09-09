<script lang="ts">
	import type { ContentViewMode } from '$lib/types';
	import { diffStore } from '$lib/stores/diff.svelte';

	const modes: { value: ContentViewMode; label: string; testId: string }[] = [
		{ value: 'raw', label: 'Raw', testId: 'view-mode-raw' },
		{ value: 'preview', label: 'Preview', testId: 'view-mode-preview' },
		{ value: 'side-by-side', label: 'Both', testId: 'view-mode-side-by-side' }
	];
</script>

<div data-testid="content-view-toggle" class="cr-segmented">
	{#each modes as mode (mode.value)}
		<button
			data-testid={mode.testId}
			class="cr-segment"
			aria-pressed={diffStore.contentViewMode === mode.value}
			onclick={() => diffStore.setContentViewMode(mode.value)}
		>
			{mode.label}
		</button>
	{/each}
</div>

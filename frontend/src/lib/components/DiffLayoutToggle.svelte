<script lang="ts">
	import type { DiffLayout } from '$lib/types';
	import { diffStore } from '$lib/stores/diff.svelte';

	const layouts: { value: DiffLayout; label: string; testId: string }[] = [
		{ value: 'unified', label: 'Unified', testId: 'layout-unified' },
		{ value: 'split', label: 'Split', testId: 'layout-split' }
	];
</script>

<div data-testid="diff-layout-toggle" class="join">
	{#each layouts as layout (layout.value)}
		<button
			data-testid={layout.testId}
			class="btn join-item btn-xs {diffStore.diffLayout === layout.value
				? 'btn-primary'
				: 'btn-outline btn-primary'}"
			aria-pressed={diffStore.diffLayout === layout.value}
			onclick={() => diffStore.setDiffLayout(layout.value)}
		>
			{layout.label}
		</button>
	{/each}
</div>

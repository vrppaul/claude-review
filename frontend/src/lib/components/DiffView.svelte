<script lang="ts">
	import { diffStore } from '$lib/stores/diff.svelte';
	import { observeFilesInView } from '$lib/utils/scroll';
	import FileSection from './FileSection.svelte';

	let container: HTMLDivElement | undefined = $state();

	// The sidebar scrolls the stream, and the stream reports back which file is
	// current — one direction each way, so the two cannot fight over it.
	$effect(() => {
		if (!container) return;
		void diffStore.files.length;

		return observeFilesInView(container, (visible) => {
			// Several sections can share the band; the earliest one is the file
			// whose header is pinned at the top.
			const current = diffStore.files.find((file) => visible.has(file.path));
			if (current) diffStore.markInView(current.path);
		});
	});
</script>

<div bind:this={container} data-testid="diff-view" class="flex-1 overflow-auto bg-base-100">
	{#each diffStore.files as file (file.path)}
		<FileSection {file} />
	{/each}
</div>

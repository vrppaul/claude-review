<script lang="ts">
	import { useReview } from '$lib/review/context';
	import FileSection from './FileSection.svelte';

	const review = useReview();

	let container: HTMLDivElement | undefined = $state();

	// The sidebar scrolls the stream, and the stream reports back which file is
	// current — one direction each way, so the two cannot fight over it.
	$effect(() => {
		if (!container) return;
		return review.sections.watchInView(container, (inBand) => {
			// Several sections can share the band; the earliest one is the file
			// whose header is pinned at the top.
			const current = review.diff.files.find((file) => inBand.has(file.path));
			if (current) review.diff.markInView(current.path);
		});
	});
</script>

<div bind:this={container} data-testid="diff-view" class="flex-1 overflow-auto bg-base-100">
	{#each review.diff.files as file (file.path)}
		<FileSection {file} scrollRoot={container ?? null} />
	{/each}
</div>

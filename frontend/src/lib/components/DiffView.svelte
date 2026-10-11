<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { reportBroken } from './broken-parts';
	import FileSection from './FileSection.svelte';
	import PartFailed from './PartFailed.svelte';

	const review = useReview();

	let container: HTMLDivElement | undefined = $state();

	// The sidebar scrolls the stream, and the stream reports back which file is
	// current — one direction each way, so the two cannot fight over it.
	$effect(() => {
		if (!container) return;
		return review.sections.watchInView(container);
	});
</script>

<div bind:this={container} data-testid="diff-view" class="flex-1 overflow-auto bg-base-100">
	{#each review.diff.files as file (file.path)}
		<!-- A file that cannot be drawn says so in its place, and takes no other file down with it -->
		<svelte:boundary onerror={reportBroken}>
			<FileSection {file} scrollRoot={container ?? null} />
			{#snippet failed(error, retry)}
				<PartFailed what={file.path} {error} {retry} />
			{/snippet}
		</svelte:boundary>
	{/each}
</div>

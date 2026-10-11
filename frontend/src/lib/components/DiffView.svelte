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
	{:else}
		<!-- The work undone and the diff taken again, say: nothing differs from
			the base. Under a narrower base the notice above the diff says so. -->
		{#if !review.diff.narrowed}
			<p data-testid="no-changes" class="cr-muted px-4 py-8 text-center text-sm">No changes found.</p>
		{/if}
	{/each}
</div>

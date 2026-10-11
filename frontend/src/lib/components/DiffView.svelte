<script lang="ts">
	import { tick, untrack } from 'svelte';
	import { useReview } from '$lib/review/context';
	import { reportBroken } from './broken-parts';
	import FileSection from './FileSection.svelte';
	import PartFailed from './PartFailed.svelte';

	const review = useReview();

	let container: HTMLElement | undefined = $state();

	// The sidebar scrolls the stream, and the stream reports back which file is
	// current — one direction each way, so the two cannot fight over it.
	$effect(() => {
		if (!container) return;
		return review.sections.watchInView(container);
	});

	// A new diff redraws what lies above the reader as well: they stay on the
	// line they were reading, not at the same distance from the top, which
	// would put them in another file. Read before the new diff is drawn, put
	// back once it is; nothing but the diff itself starts it.
	$effect.pre(() => {
		void review.diff.files;
		const area = untrack(() => container);
		const place = area ? untrack(() => review.sections.readingPlace(area)) : null;
		if (!area || place === null) return;
		void tick().then(() => review.sections.returnTo(area, place));
	});
</script>

<!-- What is reviewed: the page's main part, beside the tree and the panel -->
<main bind:this={container} data-testid="diff-view" class="cr-diff-area bg-base-100">
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
</main>

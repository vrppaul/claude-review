<script lang="ts">
	import { tick, untrack } from 'svelte';
	import { threadsOffTheDiff } from '$lib/anchors/placement';
	import { provideScrollArea } from '$lib/dom/scroll-area';
	import { useReview } from '$lib/review/context';
	import EmptyNote from '$lib/ui/EmptyNote.svelte';
	import type { CountedWords } from '$lib/utils/words';
	import { reportBroken } from './broken-parts';
	import FileSection from './FileSection.svelte';
	import PartFailed from './PartFailed.svelte';
	import UnplacedThreads from './UnplacedThreads.svelte';

	const review = useReview();

	// Threads on a file the diff no longer has, drawn above the files so none
	// leaves the screen. Under a narrower base the notice above the diff names
	// every thread it cannot draw, and takes the reader to it on the whole diff.
	const offTheDiff = $derived(review.diff.narrowed ? [] : threadsOffTheDiff(review.threads.onLines, review.diff.files));

	/** Why threads are drawn above every file, of one and of several: the file they hang on is not in the diff. */
	function offTheDiffWords(file: string): CountedWords {
		return {
			one: `comment on ${file}, a file no longer in the diff`,
			many: `comments on ${file}, a file no longer in the diff`
		};
	}

	let container: HTMLElement | undefined = $state();
	// Every file's section scrolls in this area, and builds its rows as it comes near it
	provideScrollArea(() => container ?? null);

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
<main bind:this={container} data-testid="diff-view" class="cr-diff-area bg-(--cr-ground-reading)">
	{#each offTheDiff as { file, threads } (file)}
		<UnplacedThreads {threads} why={offTheDiffWords(file)} />
	{/each}
	{#each review.diff.files as file (file.path)}
		<!-- A file that cannot be drawn says so in its place, and takes no other file down with it -->
		<svelte:boundary onerror={reportBroken}>
			<FileSection {file} />
			{#snippet failed(error, retry)}
				<PartFailed what={file.path} {error} {retry} />
			{/snippet}
		</svelte:boundary>
	{:else}
		<!-- The work undone and the diff taken again, say: nothing differs from
			the base. Under a narrower base the notice above the diff says so. -->
		{#if !review.diff.narrowed}
			<EmptyNote within="view" testId="no-changes">No changes found.</EmptyNote>
		{/if}
	{/each}
</main>

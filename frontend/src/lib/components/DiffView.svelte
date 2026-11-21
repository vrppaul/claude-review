<script lang="ts">
	import { tick, untrack } from 'svelte';
	import { provideScrollArea } from '$lib/dom/scroll-area';
	import { provideNamesInTheCode, useReview } from '$lib/review/context';
	import { threadsAboveTheFiles } from '$lib/review/files-way';
	import EmptyNote from '$lib/ui/EmptyNote.svelte';
	import { namesTheFileAsItStands } from '$lib/utils/line-places';
	import type { CountedWords } from '$lib/utils/words';
	import { reportBroken } from './broken-parts';
	import FileSection from './FileSection.svelte';
	import CodeNameLookup from './CodeNameLookup.svelte';
	import PartFailed from './PartFailed.svelte';
	import UnplacedThreads from './UnplacedThreads.svelte';

	const review = useReview();

	// Why a thread's file is not among the files drawn: the review's own change holds it still where its change is
	// whitespace alone and whitespace is left out; it holds it no more where the file is gone
	const CHANGED_IN_WHITESPACE_ALONE = 'a file changed in whitespace alone';
	const NO_LONGER_IN_THE_DIFF = 'a file no longer in the diff';

	// Threads on a file the diff on screen draws none of, drawn above the files so none
	// leaves the screen. Under a narrower base the notice above the diff names
	// every thread it cannot draw, and takes the reader to it on the whole diff.
	const offTheDiff = $derived(threadsAboveTheFiles(review.threads, review.diff));

	/** Why threads are drawn above every file, of one and of several. */
	function offTheDiffWords(file: string): CountedWords {
		const why = review.diff.holds(file) ? CHANGED_IN_WHITESPACE_ALONE : NO_LONGER_IN_THE_DIFF;
		return { one: `comment on ${file}, ${why}`, many: `comments on ${file}, ${why}` };
	}

	let container: HTMLElement | undefined = $state();
	// Every file's section scrolls in this area, and builds its rows as it comes near it
	provideScrollArea(() => container ?? null);
	// A name pressed in any file is looked up in this area, its pane standing by it
	const names = provideNamesInTheCode(review);

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
		const place = untrack(() => review.sections.readingPlace(namesTheFileAsItStands));
		if (place === null) return;
		void tick().then(() => review.sections.returnTo(place));
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
	{#if names}
		<CodeNameLookup {names} />
	{/if}
</main>

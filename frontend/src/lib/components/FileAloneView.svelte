<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import { provideScrollArea } from '$lib/dom/scroll-area';
	import { useReview } from '$lib/review/context';
	import { fileSectionKey } from '$lib/review/reading-view';
	import Bar from '$lib/ui/Bar.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import { languageOf } from '$lib/utils/highlight';
	import { EVERY_LINE } from './file-drawing.svelte';
	import FileTitle from './FileTitle.svelte';
	import LinesSection from './LinesSection.svelte';
	import { keepPlaceRead } from './place-kept.svelte';

	// What the bar says of the file, where a file of the change says what became of it
	const NOT_IN_THIS_CHANGE = 'not in this change';

	const review = useReview();
	const alone = review.views.fileAlone;

	const path = $derived(alone.path);
	const file = $derived(alone.file);
	const failure = $derived(alone.failure);
	const threads = $derived(path === null ? 0 : review.threads.onLinesOf(path).length);

	let container: HTMLElement | undefined = $state();
	// The file's section scrolls in this area, and builds its rows as it comes near it
	provideScrollArea(() => container ?? null);
	// What takes the keyboard once a read asked for again is done, the button that asked for it gone
	let putAwayButton: HTMLButtonElement | undefined = $state();

	// Where the reader reads is the section at the top of this area
	$effect(() => {
		if (!container) return;
		return review.sections.watchInView(container);
	});

	// The file read anew for a take leaves the reader on the line they read
	keepPlaceRead(review.sections, () => file);

	/** Read the file again after a read that failed. */
	async function readAgain(file: string) {
		await alone.open(file);
		focusWhatRemains(() => putAwayButton);
	}
</script>

<!-- The file's bar: its path, that the change did not touch it, its threads, and at its far end the way out of it,
	where a file of the change is marked viewed and folded -->
{#snippet bar(shown: string)}
	<Bar heads="section" testId="file-alone-header">
		<FileTitle
			path={shown}
			formerPath={null}
			element="h2"
			testId="file-alone-heading"
			became={NOT_IN_THIS_CHANGE}
			changed={null}
			{threads}
		/>
		<div class="flex-1"></div>
		<Button
			bind:element={putAwayButton}
			tone="quiet"
			size="xs"
			testId="put-file-away"
			onclick={() => void review.navigator.putAway(shown)}
		>
			<!-- The button says which file it puts away -->
			Put away<span class="sr-only">: {shown}</span>
		</Button>
	</Bar>
{/snippet}

<!-- A file of the take the change did not touch, read alone in place of the change's files: whole, from its first
	line to its last, in one column whatever layout the reader chose for a change, so scrolling never leads into
	another file -->
<main bind:this={container} data-testid="file-alone-view" class="cr-diff-area bg-(--cr-ground-reading)">
	{#if path !== null}
		{#key path}
			{#if file !== null}
				<!-- As last read, while a read anew is on its way -->
				<LinesSection
					sectionKey={fileSectionKey(path)}
					{file}
					language={languageOf(review.mode, path)}
					view="raw"
					extent={EVERY_LINE}
					folded={false}
					testId="file-alone"
				>
					{#snippet header()}
						{@render bar(path)}
					{/snippet}
				</LinesSection>
			{:else}
				<!-- First on its way, or not read: the bar stands all the same, with the way out of the file -->
				<section data-testid="file-alone">
					{@render bar(path)}
					{#if failure !== null}
						<!-- Why, under the bar, and the act to read it again -->
						<div class="flex flex-wrap items-center gap-2 px-4 py-3">
							<Failure stands="inline" testId="file-alone-failed" said={failure} />
							<Button tone="quiet" size="xs" testId="read-file-again" onclick={() => readAgain(path)}>Try again</Button>
						</div>
					{/if}
				</section>
			{/if}
		{/key}
	{/if}
</main>

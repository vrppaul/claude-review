<script lang="ts">
	import { provideScrollArea } from '$lib/dom/scroll-area';
	import { useReview } from '$lib/review/context';
	import { OVERVIEW_PART } from '$lib/review/story-keys';
	import ChapterBar from './ChapterBar.svelte';
	import StoryChapter from './StoryChapter.svelte';
	import StoryHousekeeping from './StoryHousekeeping.svelte';
	import StoryLeftOut from './StoryLeftOut.svelte';
	import StoryOverview from './StoryOverview.svelte';
	import StoryWaiting from './StoryWaiting.svelte';

	const review = useReview();

	const held = $derived(review.story.held);
	// What the reader waits on while no story is held: nothing, once one is
	const wait = $derived(review.story.wait);
	const contents = $derived(review.story.contents);

	let container: HTMLElement | undefined = $state();
	// Every piece of the story scrolls in this area, and builds its rows as it comes near it
	provideScrollArea(() => container ?? null);
	// Where what the reader waits on stands, while there is no story
	let waitingRoom: HTMLElement | undefined = $state();

	// A story drawn here is one the reader has been shown: one told while they read the files is new to
	// them no longer
	$effect(() => {
		if (held !== null) review.story.seen();
	});

	// A story told takes the place of what the reader waited on, and whatever held the keyboard there
	// goes with it. Looked at before the page redraws: the keyboard then goes to the head of the story,
	// which is the head of its overview
	$effect.pre(() => {
		if (held !== null && waitingRoom?.contains(document.activeElement)) review.parts.keyboardToHeadOf(OVERVIEW_PART);
	});

	// The story reports which piece is being read, as the files' view does of its files
	$effect(() => {
		if (!container) return;
		return review.sections.watchInView(container);
	});
	// And which part of it: the overview and a chapter's head are read before any piece is
	$effect(() => {
		if (!container) return;
		return review.parts.watchInView(container);
	});
</script>

<!-- The same change, read as the agent tells it: one scroll, the overview first, then every chapter in a
	row, then what no step tells and what the agent called housekeeping. Over it, deep in a chapter, the
	bar that says which. Until a story is told, what the reader waits on stands in its place -->
<main bind:this={container} data-testid="story-view" class="cr-diff-area bg-base-100">
	{#if wait !== null}
		<div bind:this={waitingRoom} class="cr-story-waiting-room">
			<StoryWaiting {wait} />
		</div>
	{:else if held !== null}
		{@const story = held.story}
		<ChapterBar />
		<article class="cr-story-measure flex flex-col gap-8 py-8">
			<StoryOverview {held} />

			{#each contents.chapters as chapter (chapter.told.id)}
				<StoryChapter {chapter} />
			{/each}

			{#if contents.leftOut.length > 0}
				<StoryLeftOut leftOut={contents.leftOut} />
			{/if}

			{#if story.housekeeping.length > 0}
				<StoryHousekeeping
					paths={story.housekeeping}
					testId="story-housekeeping"
					class="cr-muted border-t border-base-300 pt-6 text-sm"
				/>
			{/if}
		</article>
	{/if}
</main>

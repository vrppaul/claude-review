<script lang="ts">
	import { provideScrollArea } from '$lib/dom/scroll-area';
	import { useReview } from '$lib/review/context';
	import ChapterBar from './ChapterBar.svelte';
	import StoryChapter from './StoryChapter.svelte';
	import StoryHousekeeping from './StoryHousekeeping.svelte';
	import StoryLeftOut from './StoryLeftOut.svelte';
	import StoryOverview from './StoryOverview.svelte';

	const review = useReview();

	const held = $derived(review.story.held);
	const contents = $derived(review.story.contents);

	let container: HTMLElement | undefined = $state();
	// Every piece of the story scrolls in this area, and builds its rows as it comes near it
	provideScrollArea(() => container ?? null);

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
	bar that says which -->
<main bind:this={container} data-testid="story-view" class="cr-diff-area bg-base-100">
	{#if held === null}
		<p data-testid="no-story" class="cr-muted px-4 py-8 text-center text-sm">
			No story has been told of this change yet. The agent that made it tells one with
			<code class="font-mono">claude-review story</code>.
		</p>
	{:else}
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

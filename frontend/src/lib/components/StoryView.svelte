<script lang="ts">
	import { provideScrollArea } from '$lib/dom/scroll-area';
	import { useReview } from '$lib/review/context';
	import { counted } from '$lib/utils/words';
	import StoryChapter from './StoryChapter.svelte';
	import StoryHead from './StoryHead.svelte';
	import StoryLeftOut from './StoryLeftOut.svelte';
	import StoryOverview from './StoryOverview.svelte';

	const review = useReview();

	const held = $derived(review.story.held);

	let container: HTMLElement | undefined = $state();
	// Every piece of the story scrolls in this area, and builds its rows as it comes near it
	provideScrollArea(() => container ?? null);

	// The story reports which piece is being read, as the files' view does of its files
	$effect(() => {
		if (!container) return;
		return review.sections.watchInView(container);
	});
</script>

<!-- The same change, read as the agent tells it: one scroll, the overview first, then every chapter in a
	row, then what no step tells and what the agent called housekeeping -->
<main bind:this={container} data-testid="story-view" class="cr-diff-area bg-base-100">
	{#if held === null}
		<p data-testid="no-story" class="cr-muted px-4 py-8 text-center text-sm">
			No story has been told of this change yet. The agent that made it tells one with
			<code class="font-mono">claude-review story</code>.
		</p>
	{:else}
		{@const story = held.story}
		<article class="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-8">
			<StoryHead {held} />
			<StoryOverview overview={story.overview} chapters={story.chapters} />

			{#each review.story.contents.chapters as chapter (chapter.told.id)}
				<StoryChapter {chapter} />
			{/each}

			{#if story.left_out.length > 0}
				<StoryLeftOut leftOut={story.left_out} />
			{/if}

			{#if story.housekeeping.length > 0}
				<details data-testid="story-housekeeping" class="cr-muted border-t border-base-300 pt-6 text-sm">
					<summary class="cursor-pointer">
						Housekeeping · {counted(story.housekeeping.length, 'file', 'files')}
					</summary>
					<ul class="mt-2 flex flex-col gap-0.5 font-mono text-xs">
						{#each story.housekeeping as path (path)}
							<li>{path}</li>
						{/each}
					</ul>
				</details>
			{/if}
		</article>
	{/if}
</main>

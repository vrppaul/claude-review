<script lang="ts">
	import type { ClassValue } from 'svelte/elements';
	import {
		blockLabel,
		OVERVIEW_LISTS_IN_ORDER,
		overviewItem,
		overviewItems,
		overviewLine,
		type OverviewBlock
	} from '$lib/anchors/story';
	import { useReview } from '$lib/review/context';
	import { OVERVIEW_PART } from '$lib/review/story-keys';
	import type { OverviewList, OverviewText, StoryHeld } from '$lib/types';
	import AskableBlock from './AskableBlock.svelte';
	import { chapterNamed } from './story-words';
	import StoryHead from './StoryHead.svelte';
	import StoryPart from './StoryPart.svelte';

	interface Props {
		/** The story as the review holds it: what its overview says, under what the change is called. */
		held: StoryHeld;
	}

	let { held }: Props = $props();

	// How the heading of each of the overview's three lines looks: what to doubt is a warning
	const HEADING_LOOKS: Record<OverviewText, ClassValue> = {
		task: 'cr-muted',
		done: 'cr-muted',
		doubt: 'font-semibold text-warning'
	};

	// What each list of the overview is headed by
	const LIST_HEADINGS: Record<OverviewList, string> = {
		decisions: 'Decided, and why',
		turned_down: 'Turned down',
		later: 'Left for later'
	};

	const review = useReview();
	const overview = $derived(held.story.overview);
	const listsSomething = $derived(OVERVIEW_LISTS_IN_ORDER.some((list) => overview[list].length > 0));
	// Whether a thread, or a comment being written, hangs under anything the lists hold: they are drawn open
	// while one does, so that nothing hung there is out of sight
	const listsHeld = $derived(
		overviewItems(overview).some(
			(item) => review.threads.onBlock(item).length > 0 || review.threads.writing.aboutBlock(item) !== undefined
		)
	);
	// Whether the lists were last left open, by the reader or by what hung under them: what goes from under
	// them closes nothing, and the keyboard it gives back to what offered it stays in sight
	let leftOpen = $state(false);

	/** A press on the lists' heading opens or folds them, but folds nothing while something hangs under them. */
	function toggleUnlessHeld(press: MouseEvent) {
		if (listsHeld) press.preventDefault();
	}
</script>

<!-- One of the overview's three lines, which the reader may ask about: what the story heads it with, then
	its words. What to doubt is a warning, and says so in yellow -->
{#snippet line(block: OverviewBlock, words: string, testId: string)}
	<AskableBlock {block} {words} {testId}>
		<!-- A term and what it says, as a list of them would be: the thread under it stands outside any list -->
		<div class="grid grid-cols-[4rem_minmax(0,1fr)] gap-x-4">
			<span role="term" class={['pt-0.5 text-xs', HEADING_LOOKS[block.text]]}>{blockLabel(block)}</span>
			<p role="definition" data-testid="block-words">{words}</p>
		</div>
	</AskableBlock>
{/snippet}

<!-- The story before its first chapter, one part of it: what the change is called, then the change in
	short. The agent's voice carries its colour down the edge -->
<StoryPart partKey={OVERVIEW_PART} testId="story-overview" class="flex flex-col gap-8">
	{#snippet head(heading)}
		<StoryHead {held} {heading} />
	{/snippet}

	<section>
		<h2 class="sr-only">The change in short</h2>
		<div data-testid="story-in-short" class="cr-agent-voice flex flex-col gap-4">
			{@render line(overviewLine('task'), overview.task, 'overview-task')}
			{@render line(overviewLine('done'), overview.done, 'overview-done')}
			{#if overview.doubt}
				{@render line(overviewLine('doubt'), overview.doubt, 'overview-doubt')}
			{/if}
		</div>
	</section>

	{#if overview.diagram}
		<!-- Drawn as its source until the page draws diagrams: nothing of what the agent sent is kept from the reader -->
		<figure data-testid="story-diagram" class="flex flex-col gap-2">
			{#if overview.diagram.caption}
				<figcaption class="cr-muted text-xs">{overview.diagram.caption}</figcaption>
			{/if}
			<pre class="overflow-x-auto rounded border border-base-300 bg-base-200 px-3 py-2 font-mono text-xs">{overview
					.diagram.mermaid}</pre>
		</figure>
	{/if}

	{#if listsSomething}
		<details data-testid="story-more" bind:open={() => listsHeld || leftOpen, (open: boolean) => (leftOpen = open)}>
			<summary
				data-testid="story-more-toggle"
				class={['text-sm', !listsHeld && 'cursor-pointer']}
				onclick={toggleUnlessHeld}
			>
				More about this change
			</summary>
			<div class="cr-agent-voice mt-3 flex flex-col gap-4">
				{#each OVERVIEW_LISTS_IN_ORDER as list (list)}
					{#if overview[list].length > 0}
						<section>
							<h3 class="cr-voice-inset cr-muted text-xs font-semibold">{LIST_HEADINGS[list]}</h3>
							<!-- Each thing listed may be asked about, as the overview's lines may -->
							<ul class="mt-2 flex flex-col gap-3 text-sm">
								{#each overview[list] as item, itemPlace (itemPlace)}
									<li>
										<AskableBlock block={overviewItem(list, itemPlace)} words={item.text} testId="overview-item">
											<p data-testid="block-words">
												{item.text}
												{#if item.chapter}
													<span class="cr-muted text-xs">— {chapterNamed(held.story.chapters, item.chapter)}</span>
												{/if}
											</p>
										</AskableBlock>
									</li>
								{/each}
							</ul>
						</section>
					{/if}
				{/each}
			</div>
		</details>
	{/if}
</StoryPart>

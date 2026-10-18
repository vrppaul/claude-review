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
	import FoldChevron from './FoldChevron.svelte';
	import StoryDiagram from './StoryDiagram.svelte';
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
	const writtenUnderLists = $derived(
		overviewItems(overview).some(
			(item) => review.threads.onBlock(item).length > 0 || review.threads.writing.aboutBlock(item) !== undefined
		)
	);
	// Whether the reader left the lists open: what goes from under them closes nothing, and the keyboard it
	// gives back to what offered it stays in sight
	let leftOpen = $state(false);
	const listsOpen = $derived(writtenUnderLists || leftOpen);

	/** A press on the lists' row opens or folds them, but folds nothing while something hangs under them. */
	function toggleUnlessWrittenUnder() {
		if (!writtenUnderLists) leftOpen = !leftOpen;
	}
</script>

<!-- One of the overview's three lines, which the reader may ask about: what the story heads it with, then
	its words. What to doubt is a warning, and says so in yellow -->
{#snippet line(block: OverviewBlock, words: string, testId: string)}
	<AskableBlock {block} {words} {testId}>
		<!-- A term and what it says, as a list of them would be: the thread under it stands outside any list. On
			a narrow screen the term stands over what it says, which keeps the line's whole width -->
		<div class="grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-[4rem_minmax(0,1fr)]">
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
		<div data-testid="story-in-short" class="cr-agent-voice cr-askable-stack">
			{@render line(overviewLine('task'), overview.task, 'overview-task')}
			{@render line(overviewLine('done'), overview.done, 'overview-done')}
			{#if overview.doubt}
				{@render line(overviewLine('doubt'), overview.doubt, 'overview-doubt')}
			{/if}
		</div>
	</section>

	{#if overview.diagram}
		<StoryDiagram diagram={overview.diagram} />
	{/if}

	{#if listsSomething}
		<!-- What more the overview lists, folded under a row whose chevron stands at its far end -->
		<div data-testid="story-more">
			<button
				type="button"
				data-testid="story-more-toggle"
				class="cr-aside-row cr-pressable"
				aria-expanded={listsOpen}
				onclick={toggleUnlessWrittenUnder}
			>
				<span class="min-w-0 flex-1">More about this change</span>
				<FoldChevron folded={!listsOpen} />
			</button>
			{#if listsOpen}
				<div class="cr-agent-voice mt-3 flex flex-col gap-4">
					{#each OVERVIEW_LISTS_IN_ORDER as list (list)}
						{#if overview[list].length > 0}
							<section>
								<h3 class="cr-voice-inset cr-muted text-xs font-semibold">{LIST_HEADINGS[list]}</h3>
								<!-- Each thing listed may be asked about, as the overview's lines may -->
								<ul class="cr-askable-stack mt-2">
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
			{/if}
		</div>
	{/if}
</StoryPart>

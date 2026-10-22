<script lang="ts">
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
	import Bands from '$lib/ui/Bands.svelte';
	import type { WashedTone } from '$lib/ui/card';
	import EdgeFrame from '$lib/ui/EdgeFrame.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import type { HeadingTone } from '$lib/ui/heading';
	import type { IconName } from '$lib/ui/icons';
	import Row from '$lib/ui/Row.svelte';
	import Tile from '$lib/ui/Tile.svelte';
	import type { TileTone } from '$lib/ui/tile';
	import AskableBlock from './AskableBlock.svelte';
	import StoryDiagram from './StoryDiagram.svelte';
	import { AGENTS_VOICE } from './story-frames';
	import { chapterNamed } from './story-words';
	import StoryHead from './StoryHead.svelte';
	import StoryPart from './StoryPart.svelte';

	interface Props {
		/** The story as the review holds it: what its overview says, under what the change is called. */
		held: StoryHeld;
	}

	let { held }: Props = $props();

	/** How one of the overview's three lines is drawn: on a card of its own, and the mark on the card's tile. */
	interface LineLook {
		/** Whose the line is, or what it is: its card, its tile and its term are drawn in it, so a tone all three have. */
		tone: WashedTone & TileTone & HeadingTone;
		mark: IconName;
	}

	// What was asked is the reader's, what was done the agent's, and what to doubt is what to look at
	const LINE_LOOKS: Record<OverviewText, LineLook> = {
		task: { tone: 'reader', mark: 'target' },
		done: { tone: 'agent', mark: 'check' },
		doubt: { tone: 'warning', mark: 'warning' }
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

<!-- One of the overview's three lines, which the reader may ask about, on a card of its own in its colour: its
	mark, what the story heads it with, then its words -->
{#snippet line(block: OverviewBlock, words: string, testId: string)}
	{@const look = LINE_LOOKS[block.text]}
	<AskableBlock {block} {words} {testId} frame={{ shape: 'card', tone: look.tone }}>
		<!-- A term and what it says, as a list of them would be: the thread under it stands outside any list -->
		<div class="flex items-start gap-3">
			<Tile tone={look.tone} icon={look.mark} />
			<div class="flex max-w-(--cr-prose-measure) min-w-0 flex-1 flex-col gap-0.5">
				<Heading tag="p" heads="list" tone={look.tone} role="term">{blockLabel(block)}</Heading>
				<p role="definition" data-testid="block-words">{words}</p>
			</div>
		</div>
	</AskableBlock>
{/snippet}

<!-- The story before its first chapter, one part of it: what the change is called, then the change in
	short, a card to each line -->
<StoryPart partKey={OVERVIEW_PART} testId="story-overview" class="flex flex-col gap-8">
	{#snippet head(heading)}
		<StoryHead {held} {heading} />
	{/snippet}

	<section>
		<Heading tag="h2" heads="part" seen={false}>The change in short</Heading>
		<Bands testId="overview-lines">
			{@render line(overviewLine('task'), overview.task, 'overview-task')}
			{@render line(overviewLine('done'), overview.done, 'overview-done')}
			{#if overview.doubt}
				{@render line(overviewLine('doubt'), overview.doubt, 'overview-doubt')}
			{/if}
		</Bands>
	</section>

	{#if overview.diagram}
		<StoryDiagram diagram={overview.diagram} />
	{/if}

	{#if listsSomething}
		<!-- What more the overview lists, folded under a row whose chevron stands at its far end -->
		<div data-testid="story-more" class="flex flex-col gap-3">
			<Row names="title" testId="story-more-toggle" folded={!listsOpen} onclick={toggleUnlessWrittenUnder}>
				{#snippet label()}
					More about this change
				{/snippet}
			</Row>
			{#if listsOpen}
				<EdgeFrame look={AGENTS_VOICE} testId="overview-lists">
					<div class="flex flex-col gap-4">
						{#each OVERVIEW_LISTS_IN_ORDER as list (list)}
							{#if overview[list].length > 0}
								<section class="flex flex-col gap-2">
									<Heading tag="h3" heads="list" tone="quiet">{LIST_HEADINGS[list]}</Heading>
									<!-- Each thing listed may be asked about, as the overview's lines may -->
									<Bands listed testId="overview-list">
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
									</Bands>
								</section>
							{/if}
						{/each}
					</div>
				</EdgeFrame>
			{/if}
		</div>
	{/if}
</StoryPart>

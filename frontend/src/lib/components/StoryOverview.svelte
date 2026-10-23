<script lang="ts">
	import { OVERVIEW_LISTS_IN_ORDER, overviewItem, overviewLine } from '$lib/anchors/story';
	import { useReview } from '$lib/review/context';
	import type { ChapterListed } from '$lib/review/story-contents';
	import { chapterPartKey, OVERVIEW_PART } from '$lib/review/story-keys';
	import type { OverviewList, StoryHeld } from '$lib/types';
	import Bands from '$lib/ui/Bands.svelte';
	import Chip from '$lib/ui/Chip.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import type { IconName } from '$lib/ui/icons';
	import ListsCard from '$lib/ui/ListsCard.svelte';
	import ListsCardRow from '$lib/ui/ListsCardRow.svelte';
	import AskableBlock from './AskableBlock.svelte';
	import StoryDiagram from './StoryDiagram.svelte';
	import StoryHead from './StoryHead.svelte';
	import StoryPart from './StoryPart.svelte';
	import TermCard from './TermCard.svelte';

	interface Props {
		/** The story as the review holds it: what its overview says, under what the change is called. */
		held: StoryHeld;
	}

	let { held }: Props = $props();

	/** How one of the overview's lists is drawn on the card of them: what it is called, and its mark. */
	interface ListLook {
		name: string;
		mark: IconName;
	}

	const LIST_LOOKS: Record<OverviewList, ListLook> = {
		decisions: { name: 'Decided, and why', mark: 'decided' },
		turned_down: { name: 'Turned down', mark: 'turned-down' },
		later: { name: 'Left for later', mark: 'left-for-later' }
	};

	// Why a list stays open while something of the reader's hangs in it, said on its fold
	const STAYS_OPEN = 'Stays open while a thread hangs in it';

	const review = useReview();
	const overview = $derived(held.story.overview);
	const listsSomething = $derived(OVERVIEW_LISTS_IN_ORDER.some((list) => overview[list].length > 0));

	/**
	 * Why a list of the overview stays open: a thread, or a comment being written, hangs under one of its items,
	 * and nothing hung there goes out of sight. None while nothing does.
	 */
	function heldOpenBecause(list: OverviewList): string | undefined {
		const hangsInIt = overview[list].some((_, item) => review.threads.hangsUnder(overviewItem(list, item)));
		return hangsInIt ? STAYS_OPEN : undefined;
	}

	/** The chapter a thing the overview lists leads to, as the story lists it; none for a thing that leads to none. */
	function chapterLedTo(chapterId: string | null): ChapterListed | null {
		return chapterId === null ? null : review.story.contents.chapterAt(chapterPartKey(chapterId));
	}
</script>

<!-- The story before its first chapter, one part of it: what the change is called, then the change in
	short, a card to each line -->
<StoryPart partKey={OVERVIEW_PART} testId="story-overview" class="flex flex-col gap-8">
	{#snippet head(heading)}
		<StoryHead {held} {heading} />
	{/snippet}

	<section>
		<Heading tag="h2" heads="part" seen={false}>The change in short</Heading>
		<Bands testId="overview-lines">
			<TermCard block={overviewLine('task')} words={overview.task} testId="overview-task" />
			<TermCard block={overviewLine('done')} words={overview.done} testId="overview-done" />
			{#if overview.doubt}
				<TermCard block={overviewLine('doubt')} words={overview.doubt} testId="overview-doubt" />
			{/if}
		</Bands>
	</section>

	{#if overview.diagram}
		<StoryDiagram diagram={overview.diagram} />
	{/if}

	{#if listsSomething}
		<!-- What else the overview lists, on one card, a row to each list that holds something: folded to its first
			words until the reader opens it, each thing in it then asked about as the overview's lines are, and
			leading to its chapter where it names one -->
		<ListsCard testId="overview-lists">
			{#each OVERVIEW_LISTS_IN_ORDER as list (list)}
				{@const items = overview[list]}
				{@const [first] = items}
				{#if first}
					<ListsCardRow
						icon={LIST_LOOKS[list].mark}
						name={LIST_LOOKS[list].name}
						count={items.length}
						firstWords={first.text}
						heldOpenBecause={heldOpenBecause(list)}
						testId="overview-list"
					>
						{#each items as item, itemPlace (itemPlace)}
							{@const chapter = chapterLedTo(item.chapter)}
							<li>
								<AskableBlock
									block={overviewItem(list, itemPlace)}
									words={item.text}
									testId="overview-item"
									frame={{ shape: 'listed' }}
								>
									<p data-testid="block-words" class="max-w-(--cr-prose-measure)">
										{item.text}
										{#if chapter}
											<Chip
												voice="agent"
												names="chapter"
												testId="item-chapter"
												onclick={() => review.parts.takeTo(chapter.part)}>{chapter.told.title}</Chip
											>
										{/if}
									</p>
								</AskableBlock>
							</li>
						{/each}
					</ListsCardRow>
				{/if}
			{/each}
		</ListsCard>
	{/if}
</StoryPart>

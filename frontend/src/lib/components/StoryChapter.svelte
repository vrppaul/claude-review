<script lang="ts">
	import { chapterText } from '$lib/anchors/story';
	import { useReview } from '$lib/review/context';
	import type { ChapterListed } from '$lib/review/story-contents';
	import Bands from '$lib/ui/Bands.svelte';
	import Callout from '$lib/ui/Callout.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import TwinChip from '$lib/ui/TwinChip.svelte';
	import AskableBlock from './AskableBlock.svelte';
	import {
		AGENT_UPDATING_REASONS,
		CHANGED_AFTER_TOLD_LEAD,
		chapterCounts,
		chapterNumber,
		stepNumber,
		stepsChanged
	} from './story-words';
	import StoryPart from './StoryPart.svelte';
	import StoryStep from './StoryStep.svelte';
	import TermCard from './TermCard.svelte';

	interface Props {
		/** The chapter as the story lists it: as told, by its place, with the files it tells and its steps. */
		chapter: ChapterListed;
	}

	let { chapter }: Props = $props();
	const review = useReview();

	const told = $derived(chapter.told);
	// What the warning of a chapter a round changed says the agent is doing about it: only while it tells the story again
	const underWay = $derived(review.story.wait?.kind === 'writing' ? AGENT_UPDATING_REASONS : undefined);
</script>

<!-- Changes that belong together: why they do, where to look hardest, then one step after another; its head as far
	above what it says as the blocks of what it says stand from one another -->
<StoryPart
	partKey={chapter.part}
	testId="story-chapter"
	class="cr-story-chapter flex flex-col gap-3 border-t border-base-300 pt-6"
>
	{#snippet head(heading)}
		<!-- Its number and title, and on their line how much it tells; where the title runs long, what the chapter tells
			goes onto a line of its own, on the chapter's edge, never squeezing the title -->
		<header class="flex flex-wrap items-center gap-x-3 gap-y-1">
			<Heading {...heading} tag="h2" heads="part" number={chapterNumber(chapter.place)} testId="part-head">
				<span data-testid="chapter-title">{told.title}</span>
			</Heading>
			<TwinChip halves={chapterCounts(chapter.files.length, chapter.steps.length)} testId="chapter-counts" />
		</header>
	{/snippet}
	<!-- What it says, under its title and one block under another, each on the chapter's own edge -->
	<Bands testId="chapter-blocks">
		{#if told.changed_steps > 0}
			<!-- A round changed code the chapter tells after it was told, as the review says: said first, since what the
				agent says below was said of the code before; and that the agent is updating it, only while it is -->
			<Callout tone="warning" lead={CHANGED_AFTER_TOLD_LEAD} {underWay} testId="chapter-changed">
				{stepsChanged(told.changed_steps)}
			</Callout>
		{/if}
		<!-- Why its changes belong together, in no frame, and where to doubt them, on a card as the overview's doubt
			is: each may be asked about, and what is asked hangs below it -->
		<AskableBlock
			block={chapterText(told.id, 'why')}
			words={told.why}
			testId="chapter-why-block"
			frame={{ shape: 'unframed' }}
		>
			<p data-testid="chapter-why" class="max-w-(--cr-prose-measure)">{told.why}</p>
		</AskableBlock>
		{#if told.doubt}
			<TermCard block={chapterText(told.id, 'doubt')} words={told.doubt} testId="chapter-doubt-block" />
		{/if}

		{#each chapter.steps as step (step.section)}
			<StoryStep {step} number={stepNumber(chapter.place, step.place)} />
		{/each}
	</Bands>
</StoryPart>

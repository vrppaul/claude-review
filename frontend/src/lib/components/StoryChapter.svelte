<script lang="ts">
	import { blockLabel, chapterText } from '$lib/anchors/story';
	import { useReview } from '$lib/review/context';
	import type { ChapterListed } from '$lib/review/story-contents';
	import Bands from '$lib/ui/Bands.svelte';
	import EdgeFrame from '$lib/ui/EdgeFrame.svelte';
	import AskableBlock from './AskableBlock.svelte';
	import { A_WARNING, AGENTS_VOICE } from './story-frames';
	import {
		AGENT_UPDATING_REASONS,
		CHANGED_AFTER_TOLD_HEAD,
		chapterNumber,
		CODE_BELOW_IS_CURRENT,
		filesAndSteps,
		stepNumber,
		stepsChanged
	} from './story-words';
	import StoryPart from './StoryPart.svelte';
	import StoryStep from './StoryStep.svelte';

	interface Props {
		/** The chapter as the story lists it: as told, by its place, with the files it tells and its steps. */
		chapter: ChapterListed;
	}

	let { chapter }: Props = $props();
	const review = useReview();

	const told = $derived(chapter.told);
</script>

<!-- What heads a warning among the chapter's words, the same over each: in the warning's colour, a line of its own -->
{#snippet warningHead(words: string)}
	<span class="block text-xs font-semibold text-warning">{words}</span>
{/snippet}

<!-- Changes that belong together: why they do, where to look hardest, then one step after another -->
<StoryPart partKey={chapter.part} testId="story-chapter" class="cr-story-chapter border-t border-base-300 pt-6">
	{#snippet head(heading)}
		<!-- Where the title runs long, what the chapter tells goes onto a line of its own, never squeezed -->
		<header class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
			<h2 {...heading} data-testid="part-head" class="flex min-w-0 items-baseline gap-3 text-lg font-semibold">
				<span class="cr-chapter-number text-sm">{chapterNumber(chapter.place)}</span>
				<span data-testid="chapter-title">{told.title}</span>
			</h2>
			<span data-testid="chapter-counts" class="cr-faint ml-auto text-xs whitespace-nowrap"
				>{filesAndSteps(chapter.files.length, chapter.steps.length)}</span
			>
		</header>
	{/snippet}
	<!-- What it says, under its title and one block under another, as far apart as each block's offer to ask
		about it is tall -->
	<Bands headed testId="chapter-blocks">
		{#if told.changed_steps > 0}
			<!-- A round changed code the chapter tells after it was told, as the review says: said first, in a
				warning's frame, since what the agent says below was said of the code before; and that the agent
				is updating it, only while it is -->
			<EdgeFrame {...A_WARNING} testId="chapter-changed">
				<p>
					{@render warningHead(CHANGED_AFTER_TOLD_HEAD)}
					{stepsChanged(told.changed_steps)}
					{CODE_BELOW_IS_CURRENT}
					{#if review.story.wait?.kind === 'writing'}
						{AGENT_UPDATING_REASONS}
					{/if}
				</p>
			</EdgeFrame>
		{/if}
		<!-- Why its changes belong together, in the agent's voice, and where to doubt them, in a warning headed as
			the warning above is: each may be asked about, and what is asked hangs below its frame -->
		<AskableBlock block={chapterText(told.id, 'why')} words={told.why} testId="chapter-why-block" frame={AGENTS_VOICE}>
			<p data-testid="chapter-why">{told.why}</p>
		</AskableBlock>
		{#if told.doubt}
			{@const doubt = chapterText(told.id, 'doubt')}
			<AskableBlock block={doubt} words={told.doubt} testId="chapter-doubt-block" frame={A_WARNING}>
				<p data-testid="chapter-doubt">
					{@render warningHead(blockLabel(doubt))}
					{told.doubt}
				</p>
			</AskableBlock>
		{/if}

		{#each chapter.steps as step (step.section)}
			<StoryStep {step} number={stepNumber(chapter.place, step.place)} />
		{/each}
	</Bands>
</StoryPart>

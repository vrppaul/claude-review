<script lang="ts">
	import { blockLabel, chapterText } from '$lib/anchors/story';
	import { useReview } from '$lib/review/context';
	import type { ChapterListed } from '$lib/review/story-contents';
	import AskableBlock from './AskableBlock.svelte';
	import {
		AGENT_UPDATING_REASONS,
		CHANGED_AFTER_TOLD_HEAD,
		chapterNumber,
		CODE_BELOW_IS_CURRENT,
		filesAndSteps,
		stepNumber,
		stepsChangedIn
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

<!-- Changes that belong together: why they do, where to look hardest, then one step after another -->
<StoryPart
	partKey={chapter.part}
	testId="story-chapter"
	class="cr-story-chapter cr-askable-stack border-t border-base-300 pt-6"
>
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
	{#if told.changed !== null}
		<!-- A round changed code the chapter tells after it was told, as the review says: said first, in a
			warning's frame, since what the agent says below was said of the code before; and that the agent
			is updating it, only while it is -->
		<p data-testid="chapter-changed" class="cr-warning-frame px-3 py-2">
			<b class="font-semibold text-warning">{CHANGED_AFTER_TOLD_HEAD}</b>
			{stepsChangedIn(told.changed.steps, told.changed.round)}
			{CODE_BELOW_IS_CURRENT}
			{#if review.story.wait?.kind === 'writing'}
				{AGENT_UPDATING_REASONS}
			{/if}
		</p>
	{/if}
	<!-- Why its changes belong together, in the agent's voice, and where to doubt them, in a warning: each
		may be asked about, and what is asked hangs below its frame -->
	<AskableBlock block={chapterText(told.id, 'why')} words={told.why} testId="chapter-why-block" frame="cr-agent-voice">
		<p data-testid="chapter-why">{told.why}</p>
	</AskableBlock>
	{#if told.doubt}
		{@const doubt = chapterText(told.id, 'doubt')}
		<!-- The warning as deep as the band reaches, so a band over the doubt stays inside it -->
		<AskableBlock block={doubt} words={told.doubt} testId="chapter-doubt-block" frame="cr-warning-frame py-2">
			<p data-testid="chapter-doubt">
				<span class="block text-xs font-semibold text-warning">{blockLabel(doubt)}</span>
				{told.doubt}
			</p>
		</AskableBlock>
	{/if}

	{#each chapter.steps as step (step.section)}
		<StoryStep {step} number={stepNumber(chapter.place, step.place)} />
	{/each}
</StoryPart>

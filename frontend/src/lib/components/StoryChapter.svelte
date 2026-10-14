<script lang="ts">
	import { blockLabel, chapterText } from '$lib/anchors/story';
	import type { ChapterListed } from '$lib/review/story-contents';
	import AskableBlock from './AskableBlock.svelte';
	import { chapterNumber, filesAndSteps, stepNumber } from './story-words';
	import StoryPart from './StoryPart.svelte';
	import StoryStep from './StoryStep.svelte';

	interface Props {
		/** The chapter as the story lists it: as told, by its place, with the files it tells and its steps. */
		chapter: ChapterListed;
	}

	let { chapter }: Props = $props();

	const told = $derived(chapter.told);
</script>

<!-- Changes that belong together: why they do, where to look hardest, then one step after another -->
<StoryPart
	partKey={chapter.part}
	testId="story-chapter"
	class="cr-story-chapter flex flex-col gap-5 border-t border-base-300 pt-6"
>
	{#snippet head(heading)}
		<header class="flex items-baseline gap-3">
			<h2 {...heading} data-testid="part-head" class="flex min-w-0 items-baseline gap-3 text-lg font-semibold">
				<span class="cr-muted text-sm font-normal">{chapterNumber(chapter.place)}</span>
				<span data-testid="chapter-title">{told.title}</span>
			</h2>
			<span class="cr-faint ml-auto text-xs">{filesAndSteps(chapter.files.length, chapter.steps.length)}</span>
		</header>
	{/snippet}
	<!-- Why its changes belong together, in the agent's voice, and where to doubt them, in a warning: each
		may be asked about, and what is asked hangs below its frame -->
	<AskableBlock block={chapterText(told.id, 'why')} words={told.why} testId="chapter-why-block" frame="cr-agent-voice">
		<p data-testid="chapter-why">{told.why}</p>
	</AskableBlock>
	{#if told.doubt}
		{@const doubt = chapterText(told.id, 'doubt')}
		<!-- The warning as deep as the band reaches, so a band over the doubt stays inside it -->
		<AskableBlock
			block={doubt}
			words={told.doubt}
			testId="chapter-doubt-block"
			frame="rounded-r border-l-2 border-warning bg-(--cr-warning-tint) py-2"
		>
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

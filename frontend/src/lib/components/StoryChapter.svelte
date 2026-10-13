<script lang="ts">
	import type { ChapterListed } from '$lib/review/story-contents';
	import { chapterEntitled, chapterNumber, filesAndSteps, stepNumber } from './story-words';
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
	label={chapterEntitled(chapter.place, told.title)}
	testId="story-chapter"
	class="cr-story-chapter flex flex-col gap-5 border-t border-base-300 pt-6"
>
	{#snippet head()}
		<header class="flex items-baseline gap-3">
			<h2 class="flex min-w-0 items-baseline gap-3 text-lg font-semibold">
				<span class="cr-muted text-sm font-normal">{chapterNumber(chapter.place)}</span>
				<span data-testid="chapter-title">{told.title}</span>
			</h2>
			<span class="cr-faint ml-auto text-xs">{filesAndSteps(chapter.files.length, chapter.steps.length)}</span>
		</header>
	{/snippet}
	<p data-testid="chapter-why" class="cr-agent-voice pl-4.5">{told.why}</p>
	{#if told.doubt}
		<p data-testid="chapter-doubt" class="rounded-r border-l-2 border-warning bg-(--cr-warning-tint) px-3 py-2">
			<span class="block text-xs font-semibold text-warning">Where to doubt</span>
			{told.doubt}
		</p>
	{/if}

	{#each chapter.steps as step (step.section)}
		<StoryStep {step} number={stepNumber(chapter.place, step.place)} />
	{/each}
</StoryPart>

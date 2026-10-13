<script lang="ts">
	import { stepSectionKey } from '$lib/review/story-pieces';
	import type { ToldChapter } from '$lib/types';
	import { counted } from '$lib/utils/words';
	import { chapterNumber, stepNumber } from './story-words';
	import StoryStep from './StoryStep.svelte';

	interface Props {
		chapter: ToldChapter;
		/** Where the chapter stands among the story's chapters: what it is numbered by. */
		chapterPlace: number;
		/** The area the story scrolls in, which a piece comes near to be built; null for the page itself. */
		scrollRoot: HTMLElement | null;
	}

	let { chapter, chapterPlace, scrollRoot }: Props = $props();
</script>

<!-- Changes that belong together: why they do, where to look hardest, then one step after another -->
<section data-testid="story-chapter" class="flex flex-col gap-5 border-t border-base-300 pt-6">
	<header class="flex items-baseline gap-3">
		<h2 class="flex min-w-0 items-baseline gap-3 text-lg font-semibold">
			<span class="cr-muted text-sm font-normal">{chapterNumber(chapterPlace)}</span>
			<span data-testid="chapter-title">{chapter.title}</span>
		</h2>
		<span class="cr-faint ml-auto text-xs">{counted(chapter.steps.length, 'step', 'steps')}</span>
	</header>
	<p data-testid="chapter-why" class="cr-agent-voice pl-4.5">{chapter.why}</p>
	{#if chapter.doubt}
		<p data-testid="chapter-doubt" class="rounded-r border-l-2 border-warning bg-(--cr-warning-tint) px-3 py-2">
			<span class="block text-xs font-semibold text-warning">Where to doubt</span>
			{chapter.doubt}
		</p>
	{/if}

	{#each chapter.steps as step, stepPlace (stepSectionKey(step))}
		<StoryStep {step} number={stepNumber(chapterPlace, stepPlace)} {scrollRoot} />
	{/each}
</section>

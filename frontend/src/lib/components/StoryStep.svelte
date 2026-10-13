<script lang="ts">
	import { stepSectionKey } from '$lib/review/story-pieces';
	import type { ToldStep } from '$lib/types';
	import { reportBroken } from './broken-parts';
	import PartFailed from './PartFailed.svelte';
	import { linesInWords, linesSaid } from './story-words';
	import StoryPiece from './StoryPiece.svelte';

	interface Props {
		step: ToldStep;
		/** The step as the story numbers it: its chapter's number, then its own. */
		number: string;
		/** The area the story scrolls in, which the step's piece comes near to be built; null for the page itself. */
		scrollRoot: HTMLElement | null;
	}

	let { step, number, scrollRoot }: Props = $props();
</script>

<div data-testid="story-step" class="flex flex-col gap-2">
	<!-- The reason above the code, never beside it: the code and the panel need the width. The number heads
		the step, and says its file and lines to whoever cannot see the piece under it -->
	<div class="cr-agent-voice flex gap-3 pl-3.5">
		<h3 class="pt-0.5 font-mono text-xs font-normal text-(--cr-agent)">
			<span data-testid="step-number">{number}</span><span class="sr-only"
				>: {step.file}, {linesInWords(step.lines)}</span
			>
		</h3>
		{#if step.reason}
			<p data-testid="step-reason" class="min-w-0">{step.reason}</p>
		{/if}
	</div>
	<!-- A piece that cannot be drawn says so in its place, and takes no other piece down with it -->
	<svelte:boundary onerror={reportBroken}>
		<StoryPiece sectionKey={stepSectionKey(step)} piece={step.piece} shows="a-step" {scrollRoot}>
			{#snippet beside()}
				<span data-testid="step-lines" class="cr-muted font-mono text-xs">{linesSaid(step.lines)}</span>
			{/snippet}
		</StoryPiece>
		{#snippet failed(error, retry)}
			<PartFailed what={step.file} {error} {retry} />
		{/snippet}
	</svelte:boundary>
</div>

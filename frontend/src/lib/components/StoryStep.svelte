<script lang="ts">
	import { stepSectionKey } from '$lib/review/story-pieces';
	import type { ToldStep } from '$lib/types';
	import { reportBroken } from './broken-parts';
	import PartFailed from './PartFailed.svelte';
	import { linesSaid, stepNamed } from './story-words';
	import StoryPiece from './StoryPiece.svelte';

	interface Props {
		step: ToldStep;
		/** The step as the story numbers it: its chapter's number, then its own. */
		number: string;
	}

	let { step, number }: Props = $props();
</script>

<div data-testid="story-step" class="flex flex-col gap-2">
	<!-- The reason above the code, never beside it: the code and the panel need the width. The number heads
		the step: it is "Step 1.2" to whoever cannot see where it stands, and the piece under it says its
		file and lines once -->
	<div class="cr-agent-voice flex gap-3 pl-3.5">
		<h3
			data-testid="step-number"
			aria-label={stepNamed(number)}
			class="pt-0.5 font-mono text-xs font-normal text-(--cr-agent)"
		>
			{number}
		</h3>
		{#if step.reason}
			<p data-testid="step-reason" class="min-w-0">{step.reason}</p>
		{/if}
	</div>
	<!-- A piece that cannot be drawn says so in its place, and takes no other piece down with it -->
	<svelte:boundary onerror={reportBroken}>
		<StoryPiece sectionKey={stepSectionKey(step)} piece={step.piece} shows="a-step">
			{#snippet beside()}
				<span data-testid="step-lines" class="cr-muted font-mono text-xs">{linesSaid(step.lines)}</span>
			{/snippet}
		</StoryPiece>
		{#snippet failed(error, retry)}
			<PartFailed what={step.file} {error} {retry} />
		{/snippet}
	</svelte:boundary>
</div>

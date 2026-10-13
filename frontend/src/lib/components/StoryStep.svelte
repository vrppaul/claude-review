<script lang="ts">
	import type { StepListed } from '$lib/review/story-contents';
	import { reportBroken } from './broken-parts';
	import PartFailed from './PartFailed.svelte';
	import { alsoInChapters, linesSaid, stepNamed } from './story-words';
	import StoryPiece from './StoryPiece.svelte';

	interface Props {
		/** The step as its chapter lists it: as told, with what its section is known by and its file as the chapter lists it. */
		step: StepListed;
		/** The step as the story numbers it: its chapter's number, then its own. */
		number: string;
	}

	let { step, number }: Props = $props();

	const told = $derived(step.told);
</script>

<!-- The reason above the code, never beside it: the code and the panel need the width. The number heads
	the step: it is "Step 1.2" to whoever cannot see where it stands, and the piece under it says its
	file and lines once -->
{#snippet numberAndReason()}
	<div class="cr-agent-voice mb-2 flex gap-3 pl-3.5">
		<h3
			data-testid="step-number"
			aria-label={stepNamed(number)}
			class="pt-0.5 font-mono text-xs font-normal text-(--cr-agent)"
		>
			{number}
		</h3>
		{#if told.reason}
			<p data-testid="step-reason" class="min-w-0">{told.reason}</p>
		{/if}
	</div>
{/snippet}

<!-- A step is one section of the page, from its number down to its last line: a reader taken to it
	reads why before the code. A piece that cannot be drawn says so in its place, under the number and
	reason it still has, and takes no other piece down with it -->
<svelte:boundary onerror={reportBroken}>
	<StoryPiece sectionKey={step.section} piece={told.piece} shows="a-step" above={numberAndReason}>
		{#snippet beside()}
			<span data-testid="step-lines" class="cr-muted font-mono text-xs">{linesSaid(told.lines)}</span>
		{/snippet}
		{#snippet atFarEnd()}
			{#if step.fileListed.alsoIn.length > 0}
				<!-- One file, several chapters: where else the agent tells of it, in the agent's colour -->
				<span data-testid="also-in" class="cr-tag text-(--cr-agent)">{alsoInChapters(step.fileListed.alsoIn)}</span>
			{/if}
		{/snippet}
	</StoryPiece>
	{#snippet failed(error, retry)}
		<!-- One block among the chapter's steps, as the section it stands in for is -->
		<div>
			{@render numberAndReason()}
			<PartFailed what={told.file} {error} {retry} />
		</div>
	{/snippet}
</svelte:boundary>

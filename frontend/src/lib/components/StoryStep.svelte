<script lang="ts">
	import { askableReason, stepReason } from '$lib/anchors/story';
	import type { StepListed } from '$lib/review/story-contents';
	import AskableBlock from './AskableBlock.svelte';
	import { reportBroken } from './broken-parts';
	import PartFailed from './PartFailed.svelte';
	import { alsoInChapters, changedStepNamed, codeNoLongerFound, linesSaid, stepNamed } from './story-words';
	import StoryPiece from './StoryPiece.svelte';

	interface Props {
		/** The step as its chapter lists it: as told, with what its section is known by and its file as the chapter lists it. */
		step: StepListed;
		/** The step as the story numbers it: its chapter's number, then its own. */
		number: string;
	}

	let { step, number }: Props = $props();

	const told = $derived(step.told);
	// Its reason, where the reader may ask about it
	const askable = $derived(askableReason(told));
	// Whether it shows code a round changed after it was told: one whose code is no longer found shows none
	const changed = $derived(told.now?.changed_since_told === true);
	// What its heading is named, with whether a round changed its code after it was told
	const named = $derived(changed ? changedStepNamed(number) : stepNamed(number));
</script>

<!-- The reason above the code, never beside it: the code and the panel need the width. The number heads
	the step: it is "Step 1.2" to whoever cannot see where it stands, and the piece under it says its
	file and lines once. A step a round changed after it was told shows the code as it now stands under
	a number and reason that step back, and is named so -->
{#snippet numberAndReason()}
	<!-- A reason may be asked about, its number banded with it, and what is asked hangs below the agent's
		voice; a step of a file no thread can name takes none -->
	<div class={['mb-2', changed && 'cr-step-changed']}>
		{#if askable !== null}
			<AskableBlock
				block={stepReason(told.file, told.lines.first)}
				words={askable}
				testId="step-reason-block"
				frame="cr-agent-voice"
			>
				{@render numberWithReason(askable)}
			</AskableBlock>
		{:else}
			<div class="cr-agent-voice cr-voice-inset">{@render numberWithReason(told.reason)}</div>
		{/if}
	</div>
{/snippet}

{#snippet numberWithReason(reason: string | null)}
	<div class="flex gap-3">
		<h3 data-testid="step-number" aria-label={named} class="pt-0.5 font-mono text-xs font-normal text-(--cr-agent)">
			{number}
		</h3>
		{#if reason}
			<p data-testid="step-reason" class="min-w-0">{reason}</p>
		{/if}
	</div>
{/snippet}

{#if step.shown === null}
	<!-- A step whose code the review cannot place in the change now: its number, its reason, and a line
		that says its code in its file is no longer found, and no code, which would be other code or a
		file's status no longer true. It draws no lines, so it is no section of the page -->
	<div data-testid="story-step-without-code">
		{@render numberAndReason()}
		<p data-testid="step-code-not-found" class="cr-voice-inset cr-muted text-xs wrap-anywhere">
			{codeNoLongerFound(told.file)}
		</p>
	</div>
{:else}
	{@const shown = step.shown}
	<!-- A step is one section of the page, from its number down to its last line: a reader taken to it
		reads why before the code. A piece that cannot be drawn says so in its place, under the number and
		reason it still has, and takes no other piece down with it -->
	<svelte:boundary onerror={reportBroken}>
		<StoryPiece sectionKey={step.section} piece={shown.piece} shows="a-step" above={numberAndReason}>
			{#snippet beside()}
				<span data-testid="step-lines" class="cr-muted font-mono text-xs">{linesSaid(shown.lines)}</span>
			{/snippet}
			{#snippet atFarEnd()}
				{#if shown.fileListed.alsoIn.length > 0}
					<!-- One file, several chapters: where else the agent tells of it, in the agent's colour -->
					<span data-testid="also-in" class="cr-tag text-(--cr-agent)">{alsoInChapters(shown.fileListed.alsoIn)}</span>
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
{/if}

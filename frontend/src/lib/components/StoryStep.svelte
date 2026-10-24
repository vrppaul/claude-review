<script lang="ts">
	import { askableReason, stepReason } from '$lib/anchors/story';
	import { useReview } from '$lib/review/context';
	import type { StepListed } from '$lib/review/story-contents';
	import Chip from '$lib/ui/Chip.svelte';
	import CodeFrame from '$lib/ui/CodeFrame.svelte';
	import CodeFrameHead from '$lib/ui/CodeFrameHead.svelte';
	import CodeFrameRow from '$lib/ui/CodeFrameRow.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import InlineCode from '$lib/ui/InlineCode.svelte';
	import Tag from '$lib/ui/Tag.svelte';
	import AskableBlock from './AskableBlock.svelte';
	import { reportBroken } from './broken-parts';
	import PartFailed from './PartFailed.svelte';
	import {
		alsoInChapter,
		CHANGED_SINCE_TOLD,
		changedStepNamed,
		CODE_NO_LONGER_FOUND,
		linesSaid,
		stepNamed
	} from './story-words';
	import StoryPiece from './StoryPiece.svelte';

	interface Props {
		/** The step as its chapter lists it: as told, with what its section is known by and its file as the chapter lists it. */
		step: StepListed;
		/** The step as the story numbers it: its chapter's number, then its own. */
		number: string;
	}

	let { step, number }: Props = $props();
	const review = useReview();

	const told = $derived(step.told);
	// Its reason, where the reader may ask about it
	const askable = $derived(askableReason(told));
	// Whether it shows code a round changed after it was told: one whose code is no longer found shows none
	const changed = $derived(told.now?.changed_since_told === true);
	// What its heading is named, with whether a round changed its code after it was told
	const named = $derived(changed ? changedStepNamed(number) : stepNamed(number));
</script>

<!-- The number heads the step, in its piece's header before its file, as a file's name heads it among the files:
	it is "Step 1.2" to whoever cannot see where it stands. A step a round changed after it was told shows the code
	as it now stands under a number and reason that step back, and is named so -->
{#snippet stepNumber()}
	<Heading tag="h3" heads="piece" tone={changed ? 'faint' : 'agent'} testId="step-number" aria-label={named}>
		{number}
	</Heading>
{/snippet}

<!-- Its reason, after the agent's avatar, marked where a round changed its code since -->
{#snippet reasonSaid(reason: string)}
	<p data-testid="step-reason" class={[changed && 'cr-faint']}>{reason}</p>
	{#if changed}
		<Tag tone="warning" testId="step-changed">{CHANGED_SINCE_TOLD}</Tag>
	{/if}
{/snippet}

<!-- The reason heads the code, never beside it: the code and the panel need the width. It is the top line of the
	step's frame, which may be asked about, and what is asked hangs under it, over the code; a step of a file no
	thread can name takes none. A step with no reason has nothing above its code -->
{#snippet reasonLine()}
	{#if askable !== null}
		<AskableBlock
			block={stepReason(told.file, told.lines.first)}
			words={askable}
			testId="step-reason-block"
			frame={{ shape: 'heading-code' }}
		>
			{@render reasonSaid(askable)}
		</AskableBlock>
	{:else if told.reason !== null}
		<CodeFrameHead testId="step-reason-line">{@render reasonSaid(told.reason)}</CodeFrameHead>
	{/if}
{/snippet}

{#if step.shown === null}
	<!-- A step whose code the review cannot place in the change now: its reason, then its number and file and a line
		that says its code is no longer found there, and no code, which would be other code or a file's status no
		longer true. It draws no lines, so it is no section of the page -->
	<CodeFrame testId="story-step-without-code">
		{@render reasonLine()}
		<CodeFrameRow testId="step-code-not-found">
			{@render stepNumber()}
			<InlineCode code={told.file} kind="path" />
			<span>{CODE_NO_LONGER_FOUND}</span>
		</CodeFrameRow>
	</CodeFrame>
{:else}
	{@const shown = step.shown}
	<!-- A step is one section of the page, from its reason down to its last line, in a frame of its own: a reader
		taken to it reads why before the code. A piece that cannot be drawn says so in its place, under the reason and
		number it still has, and takes no other piece down with it -->
	<svelte:boundary onerror={reportBroken}>
		<CodeFrame testId="step-frame">
			<StoryPiece
				sectionKey={step.section}
				piece={shown.piece}
				shows="a-step"
				above={told.reason === null ? undefined : reasonLine}
				numbered={stepNumber}
			>
				{#snippet beside()}
					<span data-testid="step-lines" class="cr-muted font-mono text-xs">{linesSaid(shown.lines)}</span>
				{/snippet}
				{#snippet afterTheFile()}
					<!-- One file, several chapters: a way to each other chapter the agent tells it in, in the agent's colour -->
					{#each shown.fileListed.alsoIn as other (other.part)}
						<Chip voice="agent" names="chapter" testId="also-in" onclick={() => review.parts.takeTo(other.part)}>
							{alsoInChapter(other.place)}
						</Chip>
					{/each}
				{/snippet}
			</StoryPiece>
		</CodeFrame>
		{#snippet failed(error, retry)}
			<CodeFrame testId="step-frame">
				{@render reasonLine()}
				<CodeFrameRow testId="step-could-not-be-drawn">{@render stepNumber()}</CodeFrameRow>
				<PartFailed what={told.file} {error} {retry} />
			</CodeFrame>
		{/snippet}
	</svelte:boundary>
{/if}

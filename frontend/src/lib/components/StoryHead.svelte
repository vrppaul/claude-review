<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import { useReview } from '$lib/review/context';
	import { OVERVIEW_PART } from '$lib/review/story-keys';
	import type { StoryHeld } from '$lib/types';
	import BreathingDots from '$lib/ui/BreathingDots.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Callout from '$lib/ui/Callout.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import InlineCode from '$lib/ui/InlineCode.svelte';
	import Standing from '$lib/ui/Standing.svelte';
	import {
		ATTACH_COMMAND,
		CODE_CURRENT,
		codeMovedOnIn,
		NOT_THE_AGENTS_OWN_CHANGE,
		RECONSTRUCTED,
		STOP_WRITING,
		WRITE_IT_AGAIN,
		WRITTEN_AGAIN
	} from './story-words';

	interface Props {
		/** The story as the review holds it: the round it was told in, and whether a later one moved its code on. */
		held: StoryHeld;
		/** What the story's title carries as the heading of the part it begins: the overview has no heading but this. */
		heading: HTMLAttributes<HTMLElement>;
	}

	let { held, heading }: Props = $props();
	const review = useReview();

	// Told from the commits by an agent that did not make the change: the story says so under its title
	const reconstructed = $derived(held.story.told_from === 'commits');
	// What the reader waits on, a round having moved the story's code on: nothing while its code is current
	const wait = $derived(review.story.wait);
	// What is said under the round of writing it again, and the act it offers, which takes the keyboard there
	let saidUnderRound: HTMLElement | undefined = $state();
	let takesKeyboard: HTMLButtonElement | undefined = $state();

	// Writing it again changes under the reader — asked for, stopped, told, the agent gone — and the act that held
	// the keyboard goes with what was said. Looked at before the page redraws: the keyboard then goes to the act said
	// now, or to the story's head where there is none
	$effect.pre(() => {
		// Looked at again whenever the wait changes
		void wait?.kind;
		if (!saidUnderRound?.contains(document.activeElement)) return;
		// Each gives the keyboard, once the page has redrawn, only while it is on nothing: the act first, so the head
		// takes it only where no act is said
		focusWhatRemains(() => takesKeyboard);
		review.parts.keyboardToHeadOf(OVERVIEW_PART);
	});
</script>

<!-- What the change is called, the round its story was told in under it, how writing it again stands once a later
	round moved its code on, and, where the agent that told it did not make the change, that the story is its reading -->
<header class="flex flex-col gap-4">
	<div class="flex flex-col items-start gap-0.5">
		<Heading {...heading} tag="h1" heads="story" testId="part-head">
			<span data-testid="story-title">{held.story.title}</span>
		</Heading>
		<!-- In the agent's colour while its code is current; in the warning's, saying when, once a later round
			moved the code on under it -->
		<Standing tone={held.moved_on === null ? 'agent' : 'warning'} stands="under-a-heading" testId="story-round">
			<Icon name="round" size="xs" />
			round {held.round}
			{#if held.moved_on === null}
				<span class="cr-muted">{CODE_CURRENT}</span>
			{:else}
				<span>{codeMovedOnIn(held.moved_on.round)}</span>
			{/if}
		</Standing>
	</div>
	{#if wait !== null}
		<!-- As board StoryWriting's states 8 to 11 draw it: under the round, how writing the story again stands, with
			the acts the wait for a story offers, by the same names -->
		<div bind:this={saidUnderRound} class="flex flex-wrap items-center gap-2" data-testid="story-rewriting">
			{#if wait.kind === 'unasked'}
				{@render writeItAgain()}
			{:else if wait.kind === 'writing'}
				<!-- What the agent does, in its colour and breathing, and the way to stop it -->
				<Standing tone="agent" stands="on-a-bar" testId="story-rewriting-words">
					<BreathingDots tone="agent" testId="story-rewriting-dots" />
					<span>{WRITTEN_AGAIN}</span>
				</Standing>
				<Button
					bind:element={takesKeyboard}
					tone="quiet"
					size="xs"
					testId="stop-writing-again"
					onclick={() => review.story.stop()}
				>
					{STOP_WRITING}
				</Button>
			{:else if wait.kind === 'nobody-attached'}
				<!-- Asked for, with nobody there to write it: how one is attached, and nothing to stop. Quiet words at
					the size of the acts beside them, a sentence that wraps in a narrow column -->
				<p class="cr-muted text-xs">
					No agent is attached to write it. Attach one with <InlineCode code={ATTACH_COMMAND} kind="command" />.
				</p>
			{:else if wait.kind === 'stopped'}
				<!-- What the reader did, in the same quiet words, and the way to have it written after all -->
				<p class="cr-muted text-xs">You stopped it.</p>
				{@render writeItAgain()}
			{/if}
		</div>
	{/if}
	{#if reconstructed}
		<Callout tone="agent" lead={RECONSTRUCTED} testId="story-reconstruction">{NOT_THE_AGENTS_OWN_CHANGE}</Callout>
	{/if}
</header>

<!-- The act that has the agent write the story again: edged and small, so the title reads first -->
{#snippet writeItAgain()}
	<Button
		bind:element={takesKeyboard}
		tone="secondary"
		size="xs"
		testId="write-stale-story-again"
		onclick={() => review.story.askFor()}
	>
		{WRITE_IT_AGAIN}
	</Button>
{/snippet}

<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import { useReview } from '$lib/review/context';
	import { OVERVIEW_PART } from '$lib/review/story-keys';
	import type { StoryHeld } from '$lib/types';
	import BreathingDots from '$lib/ui/BreathingDots.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Callout from '$lib/ui/Callout.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Standing from '$lib/ui/Standing.svelte';
	import { CODE_CURRENT, codeMovedOnIn, NOT_THE_AGENTS_OWN_CHANGE, RECONSTRUCTED, WRITTEN_AGAIN } from './story-words';

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
	// The agent writes the story again, a round having moved its code on: said under the round, with the way to stop
	const writtenAgain = $derived(review.story.wait?.kind === 'writing');
	// What says it is written again, and so holds its stop
	let writingAgain: HTMLElement | undefined = $state();

	// Stopped, or told, the line goes with the stop that held the keyboard: the story's head takes it. Looked at
	// before the page redraws, while the line still holds it
	$effect.pre(() => {
		if (!writtenAgain && writingAgain?.contains(document.activeElement)) {
			review.parts.keyboardToHeadOf(OVERVIEW_PART);
		}
	});
</script>

<!-- What the change is called, the round its story was told in under it, and, where the agent that told it did not
	make the change, that the story is its reading -->
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
	{#if writtenAgain}
		<!-- As board StoryWriting's state 9 draws it: what the agent does, in its colour and breathing, and the
			stop the wait for a story offers, by the same name -->
		<div bind:this={writingAgain} class="flex flex-wrap items-center gap-2" data-testid="story-written-again">
			<Standing tone="agent" stands="on-a-bar" testId="story-written-again-words">
				<BreathingDots tone="agent" testId="story-written-again-dots" />
				<span>{WRITTEN_AGAIN}</span>
			</Standing>
			<Button tone="quiet" size="xs" testId="stop-writing-again" onclick={() => review.story.stop()}>
				Stop writing
			</Button>
		</div>
	{/if}
	{#if reconstructed}
		<Callout tone="agent" lead={RECONSTRUCTED} testId="story-reconstruction">{NOT_THE_AGENTS_OWN_CHANGE}</Callout>
	{/if}
</header>

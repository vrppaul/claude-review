<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import type { StoryHeld } from '$lib/types';
	import Callout from '$lib/ui/Callout.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Standing from '$lib/ui/Standing.svelte';
	import { CODE_CURRENT, codeMovedOnIn, NOT_THE_AGENTS_OWN_CHANGE, RECONSTRUCTED } from './story-words';

	interface Props {
		/** The story as the review holds it: the round it was told in, and whether a later one moved its code on. */
		held: StoryHeld;
		/** What the story's title carries as the heading of the part it begins: the overview has no heading but this. */
		heading: HTMLAttributes<HTMLElement>;
	}

	let { held, heading }: Props = $props();

	// Told from the commits by an agent that did not make the change: the story says so under its title
	const reconstructed = $derived(held.story.told_from === 'commits');
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
	{#if reconstructed}
		<Callout tone="agent" lead={RECONSTRUCTED} testId="story-reconstruction">{NOT_THE_AGENTS_OWN_CHANGE}</Callout>
	{/if}
</header>

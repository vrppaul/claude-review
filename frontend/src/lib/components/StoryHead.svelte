<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import type { StoryHeld } from '$lib/types';
	import EdgeFrame from '$lib/ui/EdgeFrame.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Tag from '$lib/ui/Tag.svelte';
	import { AGENTS_READING } from './story-frames';
	import { CODE_CURRENT, codeMovedOnIn } from './story-words';

	interface Props {
		/** The story as the review holds it: the round it was told in, and whether a later one moved its code on. */
		held: StoryHeld;
		/** What the story's title carries as the heading of the part it begins: the overview has no heading but this. */
		heading: HTMLAttributes<HTMLHeadingElement>;
	}

	let { held, heading }: Props = $props();

	// Told from the commits by an agent that did not make the change: the story says so wherever it speaks of itself
	const reconstructed = $derived(held.story.told_from === 'commits');
</script>

<!-- What the change is called, the round its story was told in, and whether the story is the memory of
	whoever made the change or a reading of it -->
<header class="flex flex-wrap items-baseline gap-3">
	<h1 {...heading} data-testid="part-head" class="text-xl font-semibold">
		<span data-testid="story-title">{held.story.title}</span>
	</h1>
	<!-- The round the story was told in, tagged as the page tags a thing: in the agent's colour while its
		code is current; in the warning's, saying when, once a later round moved the code on under it -->
	<Tag tone={held.moved_on === null ? 'agent' : 'warning'} testId="story-round">
		<Icon name="round" size="xs" />
		round {held.round}
		{#if held.moved_on === null}
			<span class="cr-muted">{CODE_CURRENT}</span>
		{:else}
			<span>{codeMovedOnIn(held.moved_on.round)}</span>
		{/if}
	</Tag>
	{#if reconstructed}
		<Tag tone="agent" testId="story-reconstructed">reconstructed</Tag>
	{/if}
</header>

{#if reconstructed}
	<EdgeFrame {...AGENTS_READING} testId="story-reconstruction">
		<p class="text-sm">
			The agent did not make this change. The reasons below are its reading of the code and of the commit messages, not
			what was decided at the time.
		</p>
	</EdgeFrame>
{/if}

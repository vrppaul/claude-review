<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import type { StoryHeld } from '$lib/types';

	interface Props {
		/** The story as the review holds it: as told, and the round it was told in. */
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
	<span data-testid="story-round" class="cr-muted text-xs">Round {held.round}</span>
	{#if reconstructed}
		<span data-testid="story-reconstructed" class="text-xs text-(--cr-agent)">reconstructed</span>
	{/if}
</header>

{#if reconstructed}
	<p data-testid="story-reconstruction" class="cr-agent-voice cr-agent-voice-reconstructed pl-4 text-sm">
		The agent did not make this change. The reasons below are its reading of the code and of the commit messages, not
		what was decided at the time.
	</p>
{/if}

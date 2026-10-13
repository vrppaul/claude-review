<script lang="ts">
	import type { StoryHeld } from '$lib/types';

	interface Props {
		/** The story as the review holds it: as told, and the round it was told in. */
		held: StoryHeld;
	}

	let { held }: Props = $props();

	// Told from the commits by an agent that did not make the change: the story says so wherever it speaks of itself
	const reconstructed = $derived(held.story.told_from === 'commits');
</script>

<!-- What the change is called, the round its story was told in, and whether the story is the memory of
	whoever made the change or a reading of it -->
<header class="flex flex-wrap items-baseline gap-3">
	<h1 data-testid="story-title" class="text-xl font-semibold">{held.story.title}</h1>
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

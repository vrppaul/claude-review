<script lang="ts">
	import { OVERVIEW_PART } from '$lib/review/story-keys';
	import type { StoryHeld } from '$lib/types';
	import { chapterNamed } from './story-words';
	import StoryHead from './StoryHead.svelte';
	import StoryPart from './StoryPart.svelte';

	interface Props {
		/** The story as the review holds it: what its overview says, under what the change is called. */
		held: StoryHeld;
	}

	let { held }: Props = $props();

	// What each list of the overview is headed by, in the order they are drawn
	const OVERVIEW_LISTS = [
		{ field: 'decisions', heading: 'Decided, and why' },
		{ field: 'turned_down', heading: 'Turned down' },
		{ field: 'later', heading: 'Left for later' }
	] as const;

	const overview = $derived(held.story.overview);
	const listsSomething = $derived(OVERVIEW_LISTS.some((list) => overview[list.field].length > 0));
</script>

<!-- The story before its first chapter, one part of it: what the change is called, then the change in
	short. The agent's voice carries its colour down the edge; what to doubt is a warning, and says so
	in yellow -->
<StoryPart partKey={OVERVIEW_PART} testId="story-overview" class="flex flex-col gap-8">
	{#snippet head(heading)}
		<StoryHead {held} {heading} />
	{/snippet}

	<section>
		<h2 class="sr-only">The change in short</h2>
		<dl class="cr-agent-voice grid grid-cols-[4rem_minmax(0,1fr)] gap-x-4 gap-y-3 pl-5">
			<dt class="cr-muted pt-0.5 text-xs">Task</dt>
			<dd>{overview.task}</dd>
			<dt class="cr-muted pt-0.5 text-xs">Done</dt>
			<dd>{overview.done}</dd>
			{#if overview.doubt}
				<dt class="pt-0.5 text-xs font-semibold text-warning">Doubt</dt>
				<dd data-testid="story-doubt">{overview.doubt}</dd>
			{/if}
		</dl>
	</section>

	{#if overview.diagram}
		<!-- Drawn as its source until the page draws diagrams: nothing of what the agent sent is kept from the reader -->
		<figure data-testid="story-diagram" class="flex flex-col gap-2">
			{#if overview.diagram.caption}
				<figcaption class="cr-muted text-xs">{overview.diagram.caption}</figcaption>
			{/if}
			<pre class="overflow-x-auto rounded border border-base-300 bg-base-200 px-3 py-2 font-mono text-xs">{overview
					.diagram.mermaid}</pre>
		</figure>
	{/if}

	{#if listsSomething}
		<details data-testid="story-more">
			<summary class="cursor-pointer text-sm">More about this change</summary>
			<div class="cr-agent-voice mt-3 flex flex-col gap-4 pl-5">
				{#each OVERVIEW_LISTS as list (list.field)}
					{#if overview[list.field].length > 0}
						<section>
							<h3 class="cr-muted text-xs font-semibold">{list.heading}</h3>
							<ul class="mt-1 flex list-disc flex-col gap-1 pl-5 text-sm">
								{#each overview[list.field] as item, itemPlace (itemPlace)}
									<li>
										{item.text}
										{#if item.chapter}
											<span class="cr-muted text-xs">— {chapterNamed(held.story.chapters, item.chapter)}</span>
										{/if}
									</li>
								{/each}
							</ul>
						</section>
					{/if}
				{/each}
			</div>
		</details>
	{/if}
</StoryPart>

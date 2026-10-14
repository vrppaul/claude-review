<script lang="ts">
	import type { ClassValue } from 'svelte/elements';
	import { blockLabel, overviewLine, type OverviewBlock } from '$lib/anchors/story';
	import { OVERVIEW_PART } from '$lib/review/story-keys';
	import type { OverviewText, StoryHeld } from '$lib/types';
	import AskableBlock from './AskableBlock.svelte';
	import { chapterNamed } from './story-words';
	import StoryHead from './StoryHead.svelte';
	import StoryPart from './StoryPart.svelte';

	interface Props {
		/** The story as the review holds it: what its overview says, under what the change is called. */
		held: StoryHeld;
	}

	let { held }: Props = $props();

	// How the heading of each of the overview's three lines looks: what to doubt is a warning
	const HEADING_LOOKS: Record<OverviewText, ClassValue> = {
		task: 'cr-muted',
		done: 'cr-muted',
		doubt: 'font-semibold text-warning'
	};

	// What each list of the overview is headed by, in the order they are drawn
	const OVERVIEW_LISTS = [
		{ field: 'decisions', heading: 'Decided, and why' },
		{ field: 'turned_down', heading: 'Turned down' },
		{ field: 'later', heading: 'Left for later' }
	] as const;

	const overview = $derived(held.story.overview);
	const listsSomething = $derived(OVERVIEW_LISTS.some((list) => overview[list.field].length > 0));
</script>

<!-- One of the overview's three lines, which the reader may ask about: what the story heads it with, then
	its words. What to doubt is a warning, and says so in yellow -->
{#snippet line(block: OverviewBlock, words: string, testId: string)}
	<AskableBlock {block} {words} {testId}>
		<!-- A term and what it says, as a list of them would be: the thread under it stands outside any list -->
		<div class="grid grid-cols-[4rem_minmax(0,1fr)] gap-x-4">
			<span role="term" class={['pt-0.5 text-xs', HEADING_LOOKS[block.text]]}>{blockLabel(block)}</span>
			<p role="definition" data-testid="block-words">{words}</p>
		</div>
	</AskableBlock>
{/snippet}

<!-- The story before its first chapter, one part of it: what the change is called, then the change in
	short. The agent's voice carries its colour down the edge -->
<StoryPart partKey={OVERVIEW_PART} testId="story-overview" class="flex flex-col gap-8">
	{#snippet head(heading)}
		<StoryHead {held} {heading} />
	{/snippet}

	<section>
		<h2 class="sr-only">The change in short</h2>
		<div data-testid="story-in-short" class="cr-agent-voice flex flex-col">
			{@render line(overviewLine('task'), overview.task, 'overview-task')}
			{@render line(overviewLine('done'), overview.done, 'overview-done')}
			{#if overview.doubt}
				{@render line(overviewLine('doubt'), overview.doubt, 'overview-doubt')}
			{/if}
		</div>
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

<script lang="ts">
	import { drawDiagram, followLinks, type Drawing } from '$lib/dom/diagram';
	import { useReview } from '$lib/review/context';
	import { chapterPartKey } from '$lib/review/story-keys';
	import type { Diagram, ToldChapter } from '$lib/types';
	import Dialog from './Dialog.svelte';
	import type { Closing } from './dialog-closing';
	import { diagramNotDrawn } from './diagram-words';

	interface Props {
		/** The change drawn, as the agent wrote it in Mermaid, and the chapter each node it links leads to. */
		diagram: Diagram;
		/** The story's chapters, which its links name by id. */
		chapters: readonly ToldChapter[];
	}

	let { diagram, chapters }: Props = $props();

	// What the drawing, and the dialog that draws it large, are called where the agent called it nothing
	const UNCAPTIONED = 'The change drawn';

	// What its two drawings are known by, on the page and to mermaid, which scopes each one's look by it
	const figureId = $props.id();
	const inlineId = `${figureId}-inline`;
	const largeId = `${figureId}-large`;
	const review = useReview();
	// The source alone: reading the story again hands over an equal diagram, which must draw nothing again
	const source = $derived(diagram.mermaid);
	const leadsTo = $derived(partsLinked(diagram.links, chapters));
	const name = $derived(diagram.caption ?? UNCAPTIONED);
	// Whether the reader opened it large
	let large = $state(false);

	/**
	 * Where each node the source links leads: the part of the chapter its link names, by the node's
	 * name. The review refuses a link to no chapter, so every link pairs with one.
	 */
	function partsLinked(links: Diagram['links'], told: readonly ToldChapter[]): Map<string, string> {
		const linked = Object.entries(links);
		return new Map(
			told.flatMap((chapter) =>
				linked
					.filter(([, chapterId]) => chapterId === chapter.id)
					.map(([node]): [string, string] => [node, chapterPartKey(chapter)])
			)
		);
	}
</script>

<!-- What the figure's caption says: what the agent called the drawing, and once it has drawn, a way to see
	it large -->
{#snippet caption(drawn: boolean)}
	{#if diagram.caption}
		<span class="cr-muted">{diagram.caption}</span>
	{/if}
	{#if drawn}
		<button
			type="button"
			data-testid="diagram-open-large"
			class="cursor-pointer text-(--cr-control) hover:underline"
			onclick={() => (large = true)}
		>
			Open large
		</button>
	{/if}
{/snippet}

<!-- A drawing as mermaid drew it, at its own size, in a box that scrolls sideways where it is wider than the
	column; a press on a node that leads somewhere is followed there. Or, where it did not draw, why, and the
	source as the agent wrote it -->
{#snippet shown(drawing: Drawing, follow: (part: string) => void)}
	{#if 'svg' in drawing}
		<div
			data-testid="diagram-drawing"
			class="overflow-x-auto"
			{@attach (box: HTMLElement) => followLinks(box, leadsTo, follow)}
		>
			{@html drawing.svg}
		</div>
	{:else}
		<p data-testid="diagram-fault" class="text-[0.8125rem] font-semibold text-warning">
			{diagramNotDrawn(drawing.fault)}
		</p>
		<pre
			data-testid="diagram-source"
			class="cr-muted overflow-x-auto rounded border border-base-300 bg-base-200 px-3 py-2.5 font-mono text-xs">{source}</pre>
	{/if}
{/snippet}

<!-- The diagram under the overview's lines: only its caption while mermaid draws it. Its caption is written
	in each branch, where the compiler sees it is the figure's own -->
<figure data-testid="story-diagram" aria-label={name} class="flex flex-col gap-2.5">
	{#await drawDiagram(source, inlineId)}
		{#if diagram.caption}
			<figcaption class="flex items-baseline gap-3 text-xs">{@render caption(false)}</figcaption>
		{/if}
	{:then drawing}
		{#if diagram.caption || 'svg' in drawing}
			<figcaption class="flex items-baseline gap-3 text-xs">{@render caption('svg' in drawing)}</figcaption>
		{/if}
		{@render shown(drawing, (part) => review.parts.goTo(part))}
	{/await}
</figure>

{#if large}
	<!-- Drawn again, not moved: a drawing's arrowheads and look hang on ids, which one drawing twice on the page
		would repeat. A press on a node closes it, then goes -->
	<Dialog label={name} data-testid="diagram-large" onClose={() => (large = false)}>
		{#snippet children({ closeThen }: Closing)}
			{#await drawDiagram(source, largeId) then drawing}
				{@render shown(drawing, (part) => closeThen(() => review.parts.goTo(part)))}
			{/await}
		{/snippet}
	</Dialog>
{/if}

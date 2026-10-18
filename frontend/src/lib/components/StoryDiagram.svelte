<script lang="ts">
	import type { ClassValue } from 'svelte/elements';
	import { drawDiagram, followLinks, type Drawing } from '$lib/dom/diagram';
	import { useReview } from '$lib/review/context';
	import { chapterPartKey } from '$lib/review/story-keys';
	import type { Diagram } from '$lib/types';
	import Button from '$lib/ui/Button.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import Dialog from './Dialog.svelte';
	import type { Closing } from './dialog-closing';
	import { diagramNotDrawn } from './diagram-words';
	import Icon from './Icon.svelte';

	interface Props {
		/** The change drawn, as the agent wrote it in Mermaid, and the chapter each node it links leads to. */
		diagram: Diagram;
	}

	let { diagram }: Props = $props();

	// What the drawing, and the dialog that draws it large, are called where the agent called it nothing
	const UNCAPTIONED = 'The change drawn';
	// How each drawing is sized: under the overview fitted to the column, opened large at its own size
	const FITTED_TO_THE_COLUMN = 'cr-diagram-fitted';
	const AT_ITS_OWN_SIZE = 'overflow-auto';

	// What its two drawings are known by, on the page and to mermaid, which scopes each one's look by it. The
	// one under the overview is kept by the story for as long as the review (`ReviewStory.diagramDrawn`), under
	// the id of the figure that drew it first, and no other figure stands on the page with it
	const figureId = $props.id();
	const inlineId = `${figureId}-inline`;
	const largeId = `${figureId}-large`;
	const review = useReview();
	// The source alone: reading the story again hands over an equal diagram, which must draw nothing again
	const source = $derived(diagram.mermaid);
	// Where each node the source links leads, by the node's name: the part of the chapter its link names.
	// The review refuses a link to no chapter, so every link leads to one
	const leadsTo = $derived(
		new Map(Object.entries(diagram.links).map(([node, chapterId]) => [node, chapterPartKey(chapterId)]))
	);
	const name = $derived(diagram.caption ?? UNCAPTIONED);
	// Whether the reader opened it large
	let large = $state(false);
</script>

<!-- What the figure's caption says: what the agent called the drawing, and once it has drawn, a way to see
	it large -->
{#snippet caption(drawn: boolean)}
	{#if diagram.caption}
		<span class="cr-muted">{diagram.caption}</span>
	{/if}
	{#if drawn}
		<Button tone="quiet" size="xs" testId="diagram-open-large" onclick={() => (large = true)}>Open large</Button>
	{/if}
{/snippet}

<!-- A drawing as mermaid drew it: under the overview fitted to the column, opened large at its own size in a
	box that scrolls where it is larger than the dialog. A press on a node that leads somewhere is followed
	there. Or, where it did not draw, why, and the source as the agent wrote it -->
{#snippet shown(drawing: Drawing, fit: ClassValue, follow: (part: string) => void)}
	{#if 'svg' in drawing}
		<div data-testid="diagram-drawing" class={fit} {@attach (box: HTMLElement) => followLinks(box, leadsTo, follow)}>
			{@html drawing.svg}
		</div>
	{:else}
		<p data-testid="diagram-fault" class="text-sm font-semibold text-warning">
			{diagramNotDrawn(drawing.fault)}
		</p>
		<pre
			data-testid="diagram-source"
			class="cr-muted overflow-x-auto rounded-(--radius-box) border border-base-300 bg-base-200 px-3 py-2.5 font-mono text-xs">{source}</pre>
	{/if}
{/snippet}

<!-- The diagram under the overview's lines: only its caption while mermaid draws it, the first time the
	story comes on screen. Its caption is written in each branch, where the compiler sees it is the figure's
	own -->
<figure data-testid="story-diagram" aria-label={name} class="flex flex-col gap-2.5">
	{#await review.story.diagramDrawn(source, (drawn) => drawDiagram(drawn, inlineId))}
		{#if diagram.caption}
			<figcaption class="flex items-center gap-3 text-xs">{@render caption(false)}</figcaption>
		{/if}
	{:then drawing}
		{#if diagram.caption || 'svg' in drawing}
			<figcaption class="flex items-center gap-3 text-xs">{@render caption('svg' in drawing)}</figcaption>
		{/if}
		{@render shown(drawing, FITTED_TO_THE_COLUMN, (part) => review.parts.goTo(part))}
	{/await}
</figure>

{#if large}
	<!-- Drawn again, not moved: a drawing's arrowheads and look hang on ids, which one drawing twice on the page
		would repeat. Headed by what it is called, beside the way to close it. A press on a node closes it, then
		goes -->
	<Dialog label={name} data-testid="diagram-large" onClose={() => (large = false)}>
		{#snippet children({ close, closeThen }: Closing)}
			<header class="mb-3 flex items-center gap-3">
				<h2 class="text-sm font-semibold">{name}</h2>
				<div class="flex-1"></div>
				<IconButton tone="quiet" size="xs" label="Close {name}" testId="diagram-close" onclick={close}>
					<Icon name="cross" />
				</IconButton>
			</header>
			{#await drawDiagram(source, largeId) then drawing}
				{@render shown(drawing, AT_ITS_OWN_SIZE, (part) => closeThen(() => review.parts.goTo(part)))}
			{/await}
		{/snippet}
	</Dialog>
{/if}

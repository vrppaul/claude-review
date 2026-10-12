<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { StoryNumbering } from '$lib/anchors/numbering';
	import { BuiltWhenNear } from '$lib/dom/built-when-near.svelte';
	import { useReview } from '$lib/review/context';
	import type { DiffFile } from '$lib/types';
	import { languageOf } from '$lib/utils/highlight';
	import ChangedLines from './ChangedLines.svelte';
	import FileBody from './FileBody.svelte';
	import { type Extent, linesView, type PieceShows } from './file-drawing.svelte';
	import { STATUS_LETTERS } from './status-letters';

	interface Props {
		/** What the piece's section is known by among those the story draws. */
		sectionKey: string;
		/** The piece of a file the review cut out: a step's lines, or what no step tells of the file. */
		piece: DiffFile;
		/** What it is cut out to show: the lines a step tells, or what no step tells of the file. */
		shows: PieceShows;
		/** Whose numbers its lines carry, as the story it is a piece of says. */
		numbering: StoryNumbering;
		/** The area the story scrolls in, which a piece comes near to be built; null for the page itself. */
		scrollRoot: HTMLElement | null;
		/** What is said beside the file's name: the lines a step tells, how much was left out. */
		beside: Snippet;
	}

	let { sectionKey, piece, shows, numbering, scrollRoot, beside }: Props = $props();
	const review = useReview();

	const status = $derived(STATUS_LETTERS[piece.status]);
	const language = $derived(languageOf(review.mode, piece.path));
	const view = $derived(linesView(review.settings.current.diff_layout, piece));
	const extent = $derived<Extent>({ kind: 'piece', shows, numbering });
	// How many rows the piece will draw, so the browser can leave it undrawn off
	// screen without the scrollbar lurching once it is drawn: at least one
	const rowCount = $derived(piece.hunks.reduce((count, hunk) => count + hunk.lines.length, 0));
	const rowsDrawn = $derived(Math.max(rowCount, 1));

	let element: HTMLElement | undefined = $state();
	const nearness = new BuiltWhenNear();

	$effect(() => (element ? review.sections.register(sectionKey, piece.path, element) : undefined));
	$effect(() => (element ? nearness.watch(element, scrollRoot) : undefined));
</script>

<section
	bind:this={element}
	data-testid="story-piece"
	data-path={piece.path}
	class="cr-section overflow-hidden rounded-md border border-base-300"
	style:--cr-rows={rowsDrawn}
>
	<div
		data-testid="story-piece-header"
		class="cr-file-header flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-base-300 bg-base-200 px-3 py-2"
	>
		<span class={['w-3 shrink-0 text-center font-mono text-xs font-semibold', status.colour]}>{status.letter}</span>
		<h3 class="min-w-0 font-mono text-xs font-semibold wrap-anywhere">{piece.path}</h3>
		{@render beside()}
		<div class="flex-1"></div>
		<ChangedLines file={piece} />
	</div>
	{#if nearness.built}
		<FileBody file={piece} {language} {view} {extent} />
	{:else}
		<div data-testid="file-placeholder" class="cr-file-placeholder"></div>
	{/if}
</section>

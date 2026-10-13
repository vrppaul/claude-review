<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { StoryNumbering } from '$lib/anchors/numbering';
	import { useReview } from '$lib/review/context';
	import type { DiffFile } from '$lib/types';
	import { languageOf } from '$lib/utils/highlight';
	import ChangedLines from './ChangedLines.svelte';
	import FileBody from './FileBody.svelte';
	import FilePath from './FilePath.svelte';
	import { type Extent, linesView, type PieceShows } from './file-drawing.svelte';
	import LinesSection from './LinesSection.svelte';
	import SectionHeader from './SectionHeader.svelte';
	import StatusLetter from './StatusLetter.svelte';

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

	const language = $derived(languageOf(review.mode, piece.path));
	const view = $derived(linesView(review.settings.current.diff_layout, piece));
	const extent = $derived<Extent>({ kind: 'piece', shows, numbering });
</script>

<!-- A piece of a file in a frame of its own. Clipped to its rounded corners, never hidden past them:
	`overflow: hidden` would make the piece what its header sticks to, and deep in a long piece the header
	would scroll away with it. Nothing of a story is folded away -->
<LinesSection
	{sectionKey}
	file={piece}
	folded={false}
	{scrollRoot}
	testId="story-piece"
	class="overflow-clip rounded-md border border-base-300"
>
	{#snippet header()}
		<SectionHeader testId="story-piece-header">
			<StatusLetter status={piece.status} />
			<h3 class="min-w-0 font-mono text-xs font-semibold wrap-anywhere"><FilePath file={piece} /></h3>
			{@render beside()}
			<div class="flex-1"></div>
			<ChangedLines file={piece} />
		</SectionHeader>
	{/snippet}
	{#snippet lines()}
		<FileBody file={piece} {language} {view} {extent} />
	{/snippet}
</LinesSection>

<script lang="ts">
	import type { Snippet } from 'svelte';
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
		/** What heads the piece above its file's name, in the same section: a step's number, over its reason. */
		above?: Snippet;
		/** What is said beside the file's name: the lines a step tells, how much was left out. */
		beside: Snippet;
	}

	// What the file's name is in the piece's header: the piece's heading, or plain words where the piece is
	// headed above it. A step is headed by its number; what no step tells has no heading but its file
	const AS_ITS_HEADING = 'h3';
	const AS_PLAIN_WORDS = 'p';

	let { sectionKey, piece, shows, above, beside }: Props = $props();
	const review = useReview();

	const fileNamed = $derived(above === undefined ? AS_ITS_HEADING : AS_PLAIN_WORDS);
	const language = $derived(languageOf(review.mode, piece.path));
	const view = $derived(linesView(review.settings.current.diff_layout, piece));
	// Its lines carry the numbers of the take the story was told of, as the story says
	const extent = $derived<Extent>({ kind: 'piece', shows, numbering: review.story.numbering });
</script>

<!-- A piece of a file in a frame of its own, under whatever heads it. Clipped to its rounded corners,
	never hidden past them: `overflow: hidden` would make the piece what its header sticks to, and deep
	in a long piece the header would scroll away with it. Nothing of a story is folded away -->
<LinesSection
	{sectionKey}
	file={piece}
	folded={false}
	testId="story-piece"
	class="overflow-clip rounded-md border border-base-300"
	{above}
>
	{#snippet header()}
		<SectionHeader testId="story-piece-header">
			<!-- What became of the file is part of its name: said with it, never before the heading it belongs to -->
			<svelte:element this={fileNamed} class="flex min-w-0 items-center gap-x-3 font-mono text-xs font-semibold">
				<StatusLetter status={piece.status} />
				<span class="min-w-0 wrap-anywhere"><FilePath file={piece} /></span>
			</svelte:element>
			{@render beside()}
			<div class="flex-1"></div>
			<ChangedLines file={piece} />
		</SectionHeader>
	{/snippet}
	{#snippet lines()}
		<FileBody file={piece} {language} {view} {extent} />
	{/snippet}
</LinesSection>

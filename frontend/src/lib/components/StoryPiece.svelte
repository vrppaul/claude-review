<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ClassValue } from 'svelte/elements';
	import { useReview } from '$lib/review/context';
	import { threadsOnThePiece } from '$lib/review/story-reading';
	import type { DiffFile } from '$lib/types';
	import Bar from '$lib/ui/Bar.svelte';
	import { languageOf } from '$lib/utils/highlight';
	import { type Extent, linesView, type PieceShows } from './file-drawing.svelte';
	import FileTitle from './FileTitle.svelte';
	import LinesSection from './LinesSection.svelte';

	interface Props {
		/** What the piece's section is known by among those the story draws. */
		sectionKey: string;
		/** The piece of a file the review cut out: a step's lines, or what no step tells of the file. */
		piece: DiffFile;
		/** What it is cut out to show: the lines a step tells, or what no step tells of the file. */
		shows: PieceShows;
		/** What heads the piece above its header, in the same section: a step's reason, where it has one. */
		above?: Snippet | undefined;
		/** What heads the header, before the file's name: a step's number, the piece's heading. */
		numbered?: Snippet;
		/** What is said beside the file's name: the lines a step tells. */
		beside?: Snippet;
		/** What follows the file and its change on the header: the ways to the other chapters that tell a step's file. */
		afterTheFile?: Snippet;
	}

	// What the file's name is in the piece's header: the piece's heading, or plain words where a step's
	// number heads it. What no step tells has no heading but its file
	const AS_ITS_HEADING = 'h3';
	const AS_PLAIN_WORDS = 'p';

	// How a piece is set among what stands round it, by what it shows: a step's inside the frame its step draws round
	// it, on the chapter's edges; what no step tells across the whole area, through the story's gutter, between rules,
	// as the files draw a file
	const SET_AMONG_ITS_NEIGHBOURS: Record<PieceShows, ClassValue | undefined> = {
		'a-step': undefined,
		'what-no-step-tells': 'cr-story-bleed border-y border-base-300'
	};

	let { sectionKey, piece, shows, above, numbered, beside, afterTheFile }: Props = $props();
	const review = useReview();

	const fileNamed = $derived(numbered === undefined ? AS_ITS_HEADING : AS_PLAIN_WORDS);
	const language = $derived(languageOf(review.mode, piece.path));
	const view = $derived(linesView(review.settings.current.diff_layout, piece));
	const extent = $derived<Extent>({ kind: 'piece', shows });
	const threads = $derived(threadsOnThePiece(sectionKey, piece.path, review.story, review.threads).length);
</script>

<!-- A piece of a file under whatever heads it, headed and drawn as the files draw a file. Nothing of a story is
	folded away -->
<LinesSection
	{sectionKey}
	file={piece}
	{language}
	{view}
	{extent}
	folded={false}
	testId="story-piece"
	class={SET_AMONG_ITS_NEIGHBOURS[shows]}
	{above}
>
	{#snippet header()}
		<Bar heads="section" testId="story-piece-header">
			{@render numbered?.()}
			<FileTitle file={piece} element={fileNamed} testId="piece-file" showsChange {threads} {beside} />
			{@render afterTheFile?.()}
		</Bar>
	{/snippet}
</LinesSection>

<script lang="ts">
	import type { DiffFile } from '$lib/types';
	import { useReview } from '$lib/review/context';
	import { type Extent, FileDrawing, type FileView } from './file-drawing.svelte';
	import FileNotes from './FileNotes.svelte';
	import PreviewView from './PreviewView.svelte';
	import RawView from './RawView.svelte';
	import SideBySideView from './SideBySideView.svelte';
	import SplitView from './SplitView.svelte';

	interface Props {
		file: DiffFile;
		/** What it is highlighted and rendered as, if anything. */
		language: string | null;
		view: FileView;
		/** How much of a file is given: the whole of it, or a piece cut out of one for a story. */
		extent: Extent;
	}

	let { file, language, view, extent }: Props = $props();
	const review = useReview();

	// Made once, whichever way the lines are laid out: switching layout prepares nothing again
	const drawing = new FileDrawing(review, {
		file: () => file,
		language: () => language,
		extent: () => extent
	});
</script>

<!-- On the window, so a drag let go anywhere — above the sticky header, say — still ends -->
<svelte:window onmouseup={() => drawing.commenting.release()} />

<!-- A file drawn as whoever draws it says: everything it is drawn by comes in here. A
	rendered preview draws no lines, and says how many comments it leaves out instead. -->
<FileNotes {file} unplaced={view === 'preview' ? [] : drawing.commenting.unplaced} />
{#if view === 'preview'}
	<PreviewView {file} />
{:else if view === 'side-by-side'}
	<SideBySideView {file} {drawing} />
{:else if view === 'split'}
	<SplitView {drawing} />
{:else}
	<RawView {drawing} />
{/if}

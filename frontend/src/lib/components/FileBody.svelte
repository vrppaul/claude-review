<script lang="ts" module>
	/** How a file's lines are drawn: rendered, rendered beside their text, in two columns, or in one. */
	export type FileView = 'preview' | 'side-by-side' | 'split' | 'raw';
</script>

<script lang="ts">
	import type { DiffFile } from '$lib/types';
	import type { RevealedContext } from '$lib/review/revealed-context.svelte';
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
		/** Whether the removed lines on screen are the review's own: see `DrawnFile`. */
		reviewOwnsRemovedLines: boolean;
		/** Where lines read in above the hunks are kept; null where the gaps are said but not read into. */
		revealed: RevealedContext | null;
	}

	let { file, language, view, reviewOwnsRemovedLines, revealed }: Props = $props();
</script>

<!-- A file drawn as whoever draws it says: everything it is drawn by comes in here -->
<FileNotes {file} />
{#if view === 'preview'}
	<PreviewView {file} />
{:else if view === 'side-by-side'}
	<SideBySideView {file} {language} {reviewOwnsRemovedLines} {revealed} />
{:else if view === 'split'}
	<SplitView {file} {language} {reviewOwnsRemovedLines} {revealed} />
{:else}
	<RawView {file} {language} {reviewOwnsRemovedLines} {revealed} />
{/if}

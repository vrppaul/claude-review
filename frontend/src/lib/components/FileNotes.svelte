<script lang="ts">
	import type { DiffFile, Thread, Unshown } from '$lib/types';
	import { useReview } from '$lib/review/context';
	import { modeChangeOf } from '$lib/utils/file-modes';
	import { wholeMegabytes } from '$lib/utils/sizes';
	import { FILE_NOT_COMMENTABLE } from './line-commenting.svelte';
	import UnplacedThreads from './UnplacedThreads.svelte';

	interface Props {
		file: DiffFile;
		/** Threads that no line drawn here can hang under. */
		unplaced: readonly Thread[];
	}

	let { file, unplaced }: Props = $props();
	const review = useReview();

	// Why a thread is drawn at the head of its file: the line it hangs on is not drawn
	const OFF_THEIR_LINES = { one: 'comment on a line no longer shown', many: 'comments on lines no longer shown' };

	// Why a file whose content changed shows none of its lines, in words
	const unshownWords: Record<Unshown, string> = {
		binary: 'Binary file — no preview',
		too_large: `Too large to show (over ${wholeMegabytes(review.limits.largest_file_shown_bytes)} MB)`
	};

	const modeChange = $derived(modeChangeOf(file));
	// A file can change without producing lines: binary content, content too
	// large to read, or a bare change of its mode. Say which, rather than
	// showing an empty panel.
	const emptyReason = $derived(
		file.hunks.length > 0
			? null
			: file.unshown
				? unshownWords[file.unshown]
				: modeChange
					? `${modeChange.what} change only`
					: 'No content changes'
	);
</script>

<!-- What the lines cannot show, above whichever way the lines are drawn -->
{#if !file.commentable}
	<div data-testid="not-commentable-note" class="cr-muted border-b border-base-300 bg-base-200 px-4 py-2 text-xs">
		{FILE_NOT_COMMENTABLE}
	</div>
{/if}

{#if modeChange}
	<div data-testid="mode-change-note" class="cr-muted border-b border-base-300 bg-base-200 px-4 py-2 font-mono text-xs">
		{modeChange.what} changed: {modeChange.from} → {modeChange.to}
	</div>
{/if}

<UnplacedThreads threads={unplaced} why={OFF_THEIR_LINES} />

{#if emptyReason}
	<div data-testid="empty-file-note" class="cr-muted px-4 py-8 text-center text-sm">
		{emptyReason}
	</div>
{/if}

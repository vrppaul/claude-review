<script lang="ts">
	import type { DiffFile, Thread, Unshown } from '$lib/types';
	import { useReview } from '$lib/review/context';
	import EmptyNote from '$lib/ui/EmptyNote.svelte';
	import NoticeBar from '$lib/ui/NoticeBar.svelte';
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
	<NoticeBar tone="quiet" testId="not-commentable-note">{FILE_NOT_COMMENTABLE}</NoticeBar>
{/if}

{#if modeChange}
	<!-- The modes as git writes them, in the code's face -->
	<NoticeBar tone="quiet" testId="mode-change-note">
		{modeChange.what} changed: <span class="font-mono">{modeChange.from} → {modeChange.to}</span>
	</NoticeBar>
{/if}

<UnplacedThreads threads={unplaced} why={OFF_THEIR_LINES} />

{#if emptyReason}
	<EmptyNote within="view" testId="empty-file-note">{emptyReason}</EmptyNote>
{/if}

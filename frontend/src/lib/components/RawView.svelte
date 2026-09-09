<script lang="ts">
	import type { DiffFile, DiffLine } from '$lib/types';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { expansionStore } from '$lib/stores/expansions.svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { indexByRow } from '$lib/utils/comment-index';
	import { highlightFile } from '$lib/utils/highlight';
	import { withRevealed } from '$lib/utils/expansions';
	import { applyWordMarks } from '$lib/utils/word-diff';
	import { createLineSelection } from '$lib/utils/line-selection.svelte';
	import CommentBox from './CommentBox.svelte';
	import CommentThread from './CommentThread.svelte';
	import HunkGap from './HunkGap.svelte';

	interface Props {
		file: DiffFile;
		language: string | null;
	}

	let { file, language }: Props = $props();

	const isDiffMode = $derived(diffStore.mode === 'diff');
	const colSpan = $derived(isDiffMode ? 4 : 2);
	// Markup per hunk per line, computed once per file rather than per row.
	// A row coloured end to end says a line changed but not where, so what
	// actually differs inside a replaced line is marked on top of the syntax.
	// Lines revealed from the file sit inside the hunk above which they were
	// read, so numbering, highlighting and anchoring need no special case.
	const shown = $derived(withRevealed(file, expansionStore.forFile(file.path)));
	const highlighted = $derived(
		highlightFile(shown, language).map((hunkHtml, i) =>
			isDiffMode ? applyWordMarks(shown.hunks[i].lines, hunkHtml) : hunkHtml
		)
	);
	// Comments indexed by the row they belong to, rather than scanned per line
	const commentsByRow = $derived(indexByRow(commentStore.comments, file.path));
	const modeChange = $derived(
		file.old_mode && file.new_mode ? `${file.old_mode} → ${file.new_mode}` : null
	);
	// A file can change without producing lines: binary content, or a bare
	// permission change. Say which, rather than showing an empty panel.
	const emptyReason = $derived(
		file.hunks.length > 0
			? null
			: file.is_binary
				? 'Binary file — no preview'
				: modeChange
					? 'Permission change only'
					: 'No content changes'
	);
	const selection = createLineSelection();

	// Compute flat line index offsets per hunk so we have unique indices across all hunks
	const hunkOffsets = $derived(
		shown.hunks.reduce<number[]>((acc, hunk, i) => {
			acc.push(i === 0 ? 0 : acc[i - 1] + shown.hunks[i - 1].lines.length);
			return acc;
		}, [])
	);

	$effect(() => {
		void file.path;
		selection.reset();
	});

	// Window-level listener so mouseup is caught even if the cursor
	// leaves this component (e.g. dragging above the sticky header)
	$effect(() => {
		const handler = () => selection.handleMouseUp();
		window.addEventListener('mouseup', handler);
		return () => window.removeEventListener('mouseup', handler);
	});

	function handleSaveComment(body: string) {
		if (!selection.commentingAt) return;
		const { side, line, endLine } = selection.commentingAt;
		commentStore.add(file.path, side, line, endLine, body);
		selection.clearCommenting();
	}

	/** One class decides a row's tint, its edge colour and its gutter colour. */
	function rowClass(type: DiffLine['type'], marked: boolean): string {
		if (marked) return 'cr-row-marked';
		if (!isDiffMode) return '';
		if (type === 'add') return 'cr-row-add';
		if (type === 'delete') return 'cr-row-del';
		return '';
	}

	function linePrefix(type: DiffLine['type']): string {
		if (type === 'add') return '+';
		if (type === 'delete') return '-';
		return ' ';
	}
</script>

<div data-testid="raw-view">
	{#if modeChange}
		<div
			data-testid="mode-change-note"
			class="border-b border-base-300 bg-base-200/50 px-4 py-2 font-mono text-xs text-base-content/60"
		>
			Permission changed: {modeChange}
		</div>
	{/if}

	{#if emptyReason}
		<div data-testid="empty-file-note" class="px-4 py-8 text-center text-sm text-base-content/50">
			{emptyReason}
		</div>
	{/if}

	{#each shown.hunks as hunk, hunkIdx (hunkIdx)}
		<div class="border-b border-base-300">
			{#if isDiffMode}
				<HunkGap path={file.path} hunks={file.hunks} index={hunkIdx} />
			{/if}
			{#if isDiffMode && hunk.header}
				<div class="border-y border-base-300 bg-base-200/60 px-4 py-1 font-mono text-xs text-base-content/45">
					{hunk.header}
				</div>
			{/if}

			<!-- Fixed layout so every hunk's gutters line up: the automatic
				algorithm sizes each table from its own rows, and a hunk whose
				line numbers are wider would step the columns out of line. -->
			<table class="cr-code w-full table-fixed border-collapse font-mono">
				<colgroup>
					{#if isDiffMode}
						<col class="w-12" />
					{/if}
					<col class="w-12" />
					{#if isDiffMode}
						<col class="w-4" />
					{/if}
					<col />
				</colgroup>
				<tbody>
					{#each hunk.lines as line, lineIdx (`${hunkIdx}-${lineIdx}`)}
						{@const flatIdx = hunkOffsets[hunkIdx] + lineIdx}
						{@const lineNo = selection.getLineNumber(line)}
						{@const side = selection.lineSide(line)}
						{@const lineComments = commentsByRow.get(`${side}:${lineNo}`)}
						{@const inRange = selection.isHighlighted(side, lineNo)}
						{@const showCommentBox = selection.commentingAt?.anchorIndex === flatIdx}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<tr
							class="cr-row {rowClass(line.type, inRange)} hover:brightness-110"
							onmouseenter={() => selection.handleMouseEnter(line, flatIdx)}
						>
							{#if isDiffMode}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<td
									class="cr-gutter w-12 cursor-pointer px-2 text-right select-none"
									onmousedown={() => selection.handleMouseDown(line, flatIdx)}
									title="Click to comment, drag for a range"
								>
									{line.old_no ?? ''}
								</td>
							{/if}
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<td
								data-testid="line-gutter"
								class="cr-gutter w-12 cursor-pointer border-r border-base-300 px-2 text-right select-none"
								onmousedown={() => selection.handleMouseDown(line, flatIdx)}
								title="Click to comment, drag for a range"
							>
								{line.new_no ?? ''}
							</td>
							{#if isDiffMode}
								<td class="cr-sign w-4 px-1 text-center select-none">
									{linePrefix(line.type)}
								</td>
							{/if}
							<td class="px-2 break-all whitespace-pre-wrap">
								{@html highlighted[hunkIdx][lineIdx]}
							</td>
						</tr>

						{#if lineComments || showCommentBox}
							<tr>
								<td colspan={colSpan}>
									{#each lineComments ?? [] as comment (comment.id)}
										<CommentThread {comment} />
									{/each}
									{#if showCommentBox}
										<CommentBox
											onSave={handleSaveComment}
											onCancel={() => selection.clearCommenting()}
											side={selection.commentingAt?.side}
											startLine={selection.commentingAt?.line}
											endLine={selection.commentingAt?.endLine}
										/>
									{/if}
								</td>
							</tr>
						{/if}
					{/each}
				</tbody>
			</table>
		</div>
	{/each}
</div>

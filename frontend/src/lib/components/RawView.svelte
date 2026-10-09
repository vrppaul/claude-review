<script lang="ts">
	import type { CommentSeverity, DiffFile, DiffLine } from '$lib/types';
	import { indexByRow } from '$lib/utils/comment-index';
	import { lineRangeLabel } from '$lib/utils/line-label';
	import { lineAnchor } from '$lib/anchors/line';
	import { highlightFile } from '$lib/utils/highlight';
	import { withRevealed } from '$lib/utils/expansions';
	import { hunkOffsets } from '$lib/utils/hunk-offsets';
	import { applyWordMarks } from '$lib/utils/word-diff';
	import { createLineSelection, getLineNumber, lineSide, rowOfLine } from '$lib/components/line-selection.svelte';
	import { LINE_NUMBER_ROLE } from '$lib/utils/keyboard';
	import { useReview } from '$lib/review/context';
	import CommentBox from './CommentBox.svelte';
	import CommentThread from './CommentThread.svelte';
	import HunkGap from './HunkGap.svelte';

	interface Props {
		file: DiffFile;
		language: string | null;
	}

	let { file, language }: Props = $props();
	const review = useReview();

	const isDiffMode = $derived(review.mode === 'diff');
	const colSpan = $derived(isDiffMode ? 4 : 2);
	// Markup per hunk per line, computed once per file rather than per row.
	// A row coloured end to end says a line changed but not where, so what
	// actually differs inside a replaced line is marked on top of the syntax.
	// Lines revealed from the file sit inside the hunk above which they were
	// read, so numbering, highlighting and anchoring need no special case.
	const shown = $derived(withRevealed(file, review.diff.revealed.forFile(file.path)));
	const highlighted = $derived(
		highlightFile(shown, language).map((hunkHtml, i) =>
			isDiffMode ? applyWordMarks(shown.hunks[i].lines, hunkHtml) : hunkHtml
		)
	);
	// Comments indexed by the row they belong to, rather than scanned per line
	const commentsByRow = $derived(indexByRow(review.threads.all, file.path, { removedLines: !review.diff.narrowed }));
	// Every line of the file in the order the rows count them, hunk after hunk
	const rows = $derived(shown.hunks.flatMap((hunk) => hunk.lines));
	const selection = createLineSelection({
		mayCommentOnRemoved: () => !review.diff.narrowed,
		longestRange: () => review.longestQuotedRange,
		rowOf: (side, lineNumber) => rowOfLine(rows, side, lineNumber)
	});

	const offsets = $derived(hunkOffsets(shown.hunks));

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

	/** Enter or Space on a line's number opens the composer there. */
	function commentOnKey(event: KeyboardEvent, line: DiffLine, index: number) {
		if (event.key !== 'Enter' && event.key !== ' ') return;
		event.preventDefault();
		selection.commentOnLine(line, index);
	}

	/** The current text of the lines being commented on. */
	const selectedText = $derived.by(() => {
		const at = selection.commentingAt;
		if (!at) return undefined;
		return shown.hunks
			.flatMap((hunk) => hunk.lines)
			.filter(
				(line) => lineSide(line) === at.side && getLineNumber(line) >= at.line && getLineNumber(line) <= at.endLine
			)
			.map((line) => line.content);
	});

	/** Where the comment being written hangs, said above its field. */
	const commentingLabel = $derived(
		selection.commentingAt
			? lineRangeLabel(selection.commentingAt.side, selection.commentingAt.line, selection.commentingAt.endLine)
			: undefined
	);

	function handleSaveComment(body: string, severity: CommentSeverity, images: string[]) {
		if (!selection.commentingAt) return;
		const { side, line, endLine } = selection.commentingAt;
		// The lines travel with the comment: once the diff is taken again
		// they are how the thread finds where it belongs
		review.threads.add({
			anchor: lineAnchor(file.path, side, line, endLine, selectedText ?? []),
			body,
			severity,
			images
		});
		selection.clearCommenting();
	}

	/** Write the comment and hand it straight to whoever is answering. */
	async function handleAskComment(body: string, severity: CommentSeverity, images: string[]) {
		if (!selection.commentingAt) return;
		const { side, line, endLine } = selection.commentingAt;
		const id = review.threads.add({
			anchor: lineAnchor(file.path, side, line, endLine, selectedText ?? []),
			body,
			severity,
			images
		});
		selection.clearCommenting();
		try {
			await review.threads.ask(id);
		} catch {
			// The comment is written either way; the thread offers to ask again
		}
	}

	/**
	 * A row's tint, edge and gutter colour.
	 *
	 * Selection is added to the change rather than replacing it: a line keeps
	 * showing what changed on it while you are writing about it.
	 */
	function rowClass(kind: DiffLine['kind'], marked: boolean): string {
		const change = !isDiffMode ? '' : kind === 'add' ? 'cr-row-add' : kind === 'delete' ? 'cr-row-del' : '';
		return marked ? `${change} cr-row-marked` : change;
	}

	function linePrefix(kind: DiffLine['kind']): string {
		if (kind === 'add') return '+';
		if (kind === 'delete') return '-';
		return ' ';
	}
</script>

<div data-testid="raw-view">
	{#each shown.hunks as hunk, hunkIdx (hunkIdx)}
		<div class="border-b border-base-300">
			{#if isDiffMode}
				<HunkGap path={file.path} hunks={file.hunks} index={hunkIdx} header={hunk.header} />
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
						{@const flatIdx = offsets[hunkIdx] + lineIdx}
						{@const lineNo = getLineNumber(line)}
						{@const side = lineSide(line)}
						{@const lineComments = commentsByRow.get(`${side}:${lineNo}`)}
						{@const inRange = selection.isHighlighted(side, lineNo)}
						{@const showCommentBox = selection.commentingAt?.anchorIndex === flatIdx}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<tr
							class="cr-row {rowClass(line.kind, inRange)} hover:brightness-110"
							onmouseenter={() => selection.handleMouseEnter(line, flatIdx)}
						>
							{#if isDiffMode}
								<td class="cr-gutter w-12 p-0 text-right select-none">
									<button
										data-testid="old-line-gutter"
										class="cr-gutter-button"
										tabindex="-1"
										aria-label="Comment on line {line.old_number ?? ''}"
										onmousedown={() => selection.handleMouseDown(line, flatIdx)}
										onkeydown={(e) => commentOnKey(e, line, flatIdx)}
									>
										{line.old_number ?? ''}
									</button>
								</td>
							{/if}
							<td class="cr-gutter w-12 border-r border-base-300 p-0 text-right select-none">
								<button
									data-testid="line-gutter"
									data-role={LINE_NUMBER_ROLE}
									data-tour="line-number"
									class="cr-gutter-button"
									aria-label="Comment on line {line.new_number ?? line.old_number ?? ''}"
									disabled={line.kind === 'delete' && review.diff.narrowed}
									title={line.kind === 'delete' && review.diff.narrowed
										? 'A removed line belongs to the base on screen. Show the whole diff to write here.'
										: undefined}
									onmousedown={() => selection.handleMouseDown(line, flatIdx)}
									onkeydown={(e) => commentOnKey(e, line, flatIdx)}
								>
									{line.new_number ?? ''}
								</button>
							</td>
							{#if isDiffMode}
								<td class="cr-sign w-4 px-1 text-center select-none">
									{linePrefix(line.kind)}
								</td>
							{/if}
							<td class="cr-code-cell px-2 pr-4 whitespace-pre-wrap">
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
											kind="new"
											onSave={handleSaveComment}
											onAsk={review.answerer.attached ? handleAskComment : undefined}
											onCancel={() => selection.clearCommenting()}
											label={commentingLabel}
											suggestFrom={selectedText}
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

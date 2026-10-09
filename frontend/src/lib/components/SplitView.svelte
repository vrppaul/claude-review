<script lang="ts">
	import type { CommentSeverity, DiffFile, DiffLine, LineSide } from '$lib/types';
	import { indexByRow } from '$lib/utils/comment-index';
	import { lineRangeLabel } from '$lib/utils/line-label';
	import { lineAnchor } from '$lib/anchors/line';
	import { highlightFile } from '$lib/utils/highlight';
	import {
		createLineSelection,
		getLineNumber,
		lineSide,
		rowOfLine
	} from '$lib/utils/line-selection.svelte';
	import { buildSplitRows, type SplitCell } from '$lib/utils/split-rows';
	import { withRevealed } from '$lib/utils/expansions';
	import { applyWordMarks } from '$lib/utils/word-diff';
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

	const shown = $derived(withRevealed(file, review.diff.revealed.forFile(file.path)));
	const highlighted = $derived(
		highlightFile(shown, language).map((hunkHtml, i) =>
			applyWordMarks(shown.hunks[i].lines, hunkHtml)
		)
	);
	const commentsByRow = $derived(
		indexByRow(review.threads.all, file.path, { removedLines: !review.diff.narrowed })
	);
	const rowsPerHunk = $derived(shown.hunks.map((hunk) => buildSplitRows(hunk.lines)));
	const hunkOffsets = $derived(
		shown.hunks.reduce<number[]>((acc, hunk, i) => {
			acc.push(i === 0 ? 0 : acc[i - 1] + shown.hunks[i - 1].lines.length);
			return acc;
		}, [])
	);

	// Every line of the file in the order the rows count them, hunk after hunk
	const rows = $derived(shown.hunks.flatMap((hunk) => hunk.lines));
	const selection = createLineSelection({
		mayCommentOnRemoved: () => !review.diff.narrowed,
		longestRange: () => review.longestQuotedRange,
		rowOf: (side, lineNumber) => rowOfLine(rows, side, lineNumber)
	});

	$effect(() => {
		void file.path;
		selection.reset();
	});

	// Window-level so a drag that leaves the table still ends
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
				(line) =>
					lineSide(line) === at.side &&
					getLineNumber(line) >= at.line &&
					getLineNumber(line) <= at.endLine
			)
			.map((line) => line.content);
	});

	/** Where the comment being written hangs, said above its field. */
	const commentingLabel = $derived(
		selection.commentingAt
			? lineRangeLabel(
					selection.commentingAt.side,
					selection.commentingAt.line,
					selection.commentingAt.endLine
				)
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

	function cellSide(cell: SplitCell): LineSide {
		return lineSide(cell.line);
	}

	function commentsFor(cell: SplitCell | undefined): ReturnType<typeof commentsByRow.get> {
		if (!cell) return undefined;
		return commentsByRow.get(`${cellSide(cell)}:${getLineNumber(cell.line)}`);
	}

	function marked(cell: SplitCell): boolean {
		return selection.isHighlighted(cellSide(cell), getLineNumber(cell.line));
	}

	/** Selection is added to the change rather than replacing it, so a line
	 * keeps showing what changed on it while you are writing about it. */
	function tint(cell: SplitCell | undefined, kind: DiffLine['kind']): string {
		if (!cell) return 'cr-cell-absent';
		const change =
			cell.line.kind === kind ? `cr-cell-${kind === 'add' ? 'add' : 'del'}` : '';
		return marked(cell) ? `${change} cr-cell-marked` : change;
	}

	function edge(cell: SplitCell | undefined, kind: DiffLine['kind']): string {
		if (!cell) return 'cr-edge';
		if (marked(cell)) return 'cr-edge cr-edge-marked';
		return cell.line.kind === kind ? `cr-edge cr-edge-${kind === 'add' ? 'add' : 'del'}` : 'cr-edge';
	}
</script>

{#snippet composer()}
	<div class="px-3 py-2">
		<CommentBox
			kind="new"
			onSave={handleSaveComment}
			onAsk={review.answerer.attached ? handleAskComment : undefined}
			onCancel={() => selection.clearCommenting()}
			label={commentingLabel}
			suggestFrom={selectedText}
		/>
	</div>
{/snippet}

<div data-testid="split-view">
	{#each shown.hunks as hunk, hunkIdx (hunkIdx)}
		<div class="border-b border-base-300">
			<HunkGap path={file.path} hunks={file.hunks} index={hunkIdx} header={hunk.header} />

			<table class="cr-code w-full table-fixed border-collapse font-mono">
				<!-- Fixed layout with both content columns unsized: the two halves
					then split what the gutters leave, so neither side is wider. -->
				<colgroup>
					<col class="w-12" />
					<col />
					<col class="w-12" />
					<col />
				</colgroup>
				<tbody>
					{#each rowsPerHunk[hunkIdx] as row, rowIdx (rowIdx)}
						{@const leftComments = commentsFor(row.left)}
						{@const rightComments =
							row.left?.line === row.right?.line ? undefined : commentsFor(row.right)}
						{@const boxAt = selection.commentingAt?.anchorIndex}
						{@const showBox =
							(row.left && hunkOffsets[hunkIdx] + row.left.index === boxAt) ||
							(row.right && hunkOffsets[hunkIdx] + row.right.index === boxAt)}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<tr data-testid="split-row" class="cr-side-del">
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<td
								class="cr-gutter w-12 p-0 text-right select-none {edge(row.left, 'delete')} {tint(
									row.left,
									'delete'
								)}"
								onmouseenter={() =>
									row.left &&
									selection.handleMouseEnter(row.left.line, hunkOffsets[hunkIdx] + row.left.index)}
							>
								{#if row.left}
									{@const cell = row.left}
									<!-- One keyboard stop per row: the new side's number, or this
										one when the row has nothing on the new side -->
									<button
										data-testid={row.right ? 'old-line-gutter' : 'line-gutter'}
										class="cr-gutter-button"
										tabindex={row.right ? -1 : 0}
										aria-label="Comment on removed line {cell.line.old_number ?? ''}"
										disabled={review.diff.narrowed}
										title={review.diff.narrowed
											? 'A removed line belongs to the base on screen. Show the whole diff to write here.'
											: undefined}
										onmousedown={() =>
											selection.handleMouseDown(cell.line, hunkOffsets[hunkIdx] + cell.index)}
										onkeydown={(e) =>
											commentOnKey(e, cell.line, hunkOffsets[hunkIdx] + cell.index)}
									>
										{cell.line.old_number ?? ''}
									</button>
								{/if}
							</td>
							<td
								data-testid="split-old-code"
								class="cr-code-cell border-r border-base-300 px-2 whitespace-pre-wrap {tint(
									row.left,
									'delete'
								)}"
							>
								{#if row.left}{@html highlighted[hunkIdx][row.left.index]}{/if}
							</td>

							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<td
								class="cr-gutter cr-side-add w-12 p-0 text-right select-none {edge(
									row.right,
									'add'
								)} {tint(row.right, 'add')}"
								onmouseenter={() =>
									row.right &&
									selection.handleMouseEnter(row.right.line, hunkOffsets[hunkIdx] + row.right.index)}
							>
								{#if row.right}
									{@const cell = row.right}
									<button
										data-testid="line-gutter" data-tour="line-number"
										class="cr-gutter-button"
										aria-label="Comment on line {cell.line.new_number ?? ''}"
										onmousedown={() =>
											selection.handleMouseDown(cell.line, hunkOffsets[hunkIdx] + cell.index)}
										onkeydown={(e) =>
											commentOnKey(e, cell.line, hunkOffsets[hunkIdx] + cell.index)}
									>
										{cell.line.new_number ?? ''}
									</button>
								{/if}
							</td>
							<td
								data-testid="split-new-code"
								class="cr-side-add cr-code-cell px-2 pr-4 whitespace-pre-wrap {tint(row.right, 'add')}"
							>
								{#if row.right}{@html highlighted[hunkIdx][row.right.index]}{/if}
							</td>
						</tr>

						{#if leftComments || rightComments || showBox}
							<!-- A comment sits under the side it is about: in two columns the
								old and the new line share a number, and a box in the wrong half
								says nothing about which one is meant. -->
							<tr>
								<td colspan="2" class="align-top">
									{#each leftComments ?? [] as comment (comment.id)}
										<CommentThread {comment} />
									{/each}
									{#if showBox && selection.commentingAt?.side === 'old'}
										{@render composer()}
									{/if}
								</td>
								<td colspan="2" class="align-top">
									{#each rightComments ?? [] as comment (comment.id)}
										<CommentThread {comment} />
									{/each}
									{#if showBox && selection.commentingAt?.side === 'new'}
										{@render composer()}
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

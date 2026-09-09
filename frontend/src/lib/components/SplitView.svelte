<script lang="ts">
	import type { CommentSeverity, DiffFile, DiffLine, LineSide } from '$lib/types';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { reviewStore } from '$lib/stores/review.svelte';
	import { expansionStore } from '$lib/stores/expansions.svelte';
	import { indexByRow } from '$lib/utils/comment-index';
	import { highlightFile } from '$lib/utils/highlight';
	import { createLineSelection } from '$lib/utils/line-selection.svelte';
	import { buildSplitRows, type SplitCell } from '$lib/utils/split-rows';
	import { withRevealed } from '$lib/utils/expansions';
	import { applyWordMarks } from '$lib/utils/word-diff';
	import CommentBox from './CommentBox.svelte';
	import CommentThread from './CommentThread.svelte';
	import HunkGap from './HunkGap.svelte';

	interface Props {
		file: DiffFile;
		language: string | null;
	}

	let { file, language }: Props = $props();

	const shown = $derived(withRevealed(file, expansionStore.forFile(file.path)));
	const highlighted = $derived(
		highlightFile(shown, language).map((hunkHtml, i) =>
			applyWordMarks(shown.hunks[i].lines, hunkHtml)
		)
	);
	const commentsByRow = $derived(indexByRow(commentStore.comments, file.path));
	const rowsPerHunk = $derived(shown.hunks.map((hunk) => buildSplitRows(hunk.lines)));
	const hunkOffsets = $derived(
		shown.hunks.reduce<number[]>((acc, hunk, i) => {
			acc.push(i === 0 ? 0 : acc[i - 1] + shown.hunks[i - 1].lines.length);
			return acc;
		}, [])
	);

	const selection = createLineSelection();

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
					selection.lineSide(line) === at.side &&
					selection.getLineNumber(line) >= at.line &&
					selection.getLineNumber(line) <= at.endLine
			)
			.map((line) => line.content);
	});

	function handleSaveComment(body: string, severity: CommentSeverity) {
		if (!selection.commentingAt) return;
		const { side, line, endLine } = selection.commentingAt;
		// The lines travel with the comment: once the diff is taken again
		// they are how the thread finds where it belongs
		commentStore.add(file.path, side, line, endLine, body, severity, selectedText ?? []);
		selection.clearCommenting();
	}

	/** Write the comment and hand it straight to whoever is answering. */
	async function handleAskComment(body: string, severity: CommentSeverity) {
		if (!selection.commentingAt) return;
		const { side, line, endLine } = selection.commentingAt;
		const id = commentStore.add(file.path, side, line, endLine, body, severity, selectedText ?? []);
		selection.clearCommenting();
		try {
			await commentStore.ask(id);
		} catch {
			// The comment is written either way; the thread offers to ask again
		}
	}

	function cellSide(cell: SplitCell): LineSide {
		return selection.lineSide(cell.line);
	}

	function commentsFor(cell: SplitCell | undefined): ReturnType<typeof commentsByRow.get> {
		if (!cell) return undefined;
		return commentsByRow.get(`${cellSide(cell)}:${selection.getLineNumber(cell.line)}`);
	}

	function marked(cell: SplitCell): boolean {
		return selection.isHighlighted(cellSide(cell), selection.getLineNumber(cell.line));
	}

	/** Selection is added to the change rather than replacing it, so a line
	 * keeps showing what changed on it while you are writing about it. */
	function tint(cell: SplitCell | undefined, type: DiffLine['type']): string {
		if (!cell) return 'cr-cell-absent';
		const change =
			cell.line.type === type ? `cr-cell-${type === 'add' ? 'add' : 'del'}` : '';
		return marked(cell) ? `${change} cr-cell-marked` : change;
	}

	function edge(cell: SplitCell | undefined, type: DiffLine['type']): string {
		if (!cell) return 'cr-edge';
		if (marked(cell)) return 'cr-edge cr-edge-marked';
		return cell.line.type === type ? `cr-edge cr-edge-${type === 'add' ? 'add' : 'del'}` : 'cr-edge';
	}
</script>

{#snippet composer()}
	<div class="px-3 py-2">
		<CommentBox
			onSave={handleSaveComment}
			onAsk={reviewStore.canSendRound ? handleAskComment : undefined}
			onCancel={() => selection.clearCommenting()}
			side={selection.commentingAt?.side}
			startLine={selection.commentingAt?.line}
			endLine={selection.commentingAt?.endLine}
			suggestFrom={selectedText}
		/>
	</div>
{/snippet}

<div data-testid="split-view">
	{#each shown.hunks as hunk, hunkIdx (hunkIdx)}
		<div class="border-b border-base-300">
			<HunkGap path={file.path} hunks={file.hunks} index={hunkIdx} />
			{#if hunk.header}
				<div
					class="cr-muted border-y border-base-300 bg-base-200 px-4 py-1 font-mono text-xs"
				>
					{hunk.header}
				</div>
			{/if}

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
						<tr class="cr-side-del">
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
									<button
										class="cr-gutter-button"
										tabindex="-1"
										aria-label="Comment on removed line {cell.line.old_no ?? ''}"
										onmousedown={() =>
											selection.handleMouseDown(cell.line, hunkOffsets[hunkIdx] + cell.index)}
										onkeydown={(e) =>
											commentOnKey(e, cell.line, hunkOffsets[hunkIdx] + cell.index)}
									>
										{cell.line.old_no ?? ''}
									</button>
								{/if}
							</td>
							<td
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
										data-testid="line-gutter"
										class="cr-gutter-button"
										aria-label="Comment on line {cell.line.new_no ?? ''}"
										onmousedown={() =>
											selection.handleMouseDown(cell.line, hunkOffsets[hunkIdx] + cell.index)}
										onkeydown={(e) =>
											commentOnKey(e, cell.line, hunkOffsets[hunkIdx] + cell.index)}
									>
										{cell.line.new_no ?? ''}
									</button>
								{/if}
							</td>
							<td class="cr-side-add cr-code-cell px-2 pr-4 whitespace-pre-wrap {tint(row.right, 'add')}">
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

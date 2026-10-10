<script lang="ts">
	import type { DiffFile, LinePlace, LineSide } from '$lib/types';
	import type { RevealedContext } from '$lib/review/revealed-context.svelte';
	import { useReview } from '$lib/review/context';
	import { type DrawnLine, drawnHunks } from '$lib/utils/drawn-file';
	import { withRevealed } from '$lib/utils/expansions';
	import { splitRows } from '$lib/utils/split-rows';
	import HunkGap from './HunkGap.svelte';
	import LineGutter from './LineGutter.svelte';
	import LineNotes from './LineNotes.svelte';
	import { LineCommenting } from './line-commenting.svelte';

	// The two columns are the two sides, the old on the left: the kind of line each colours as changed
	const CHANGED_IN: Record<LineSide, 'delete' | 'add'> = { old: 'delete', new: 'add' };
	// How a cell is tinted, and how its edge is coloured, when its line changed
	const TINTS: Record<LineSide, string> = { old: 'cr-cell-del', new: 'cr-cell-add' };
	const EDGES: Record<LineSide, string> = { old: 'cr-edge-del', new: 'cr-edge-add' };

	interface Props {
		file: DiffFile;
		language: string | null;
		/** Whether the removed lines on screen are the review's own: see `DrawnFile`. */
		reviewOwnsRemovedLines: boolean;
		/** Where lines read in above the hunks are kept; null where the gaps are said but not read into. */
		revealed: RevealedContext | null;
	}

	let { file, language, reviewOwnsRemovedLines, revealed }: Props = $props();
	const review = useReview();

	const shown = $derived(revealed ? withRevealed(file, revealed.forFile(file.path)) : file);
	const hunks = $derived(drawnHunks(shown, language, true));
	const commenting = new LineCommenting(review, {
		path: () => file.path,
		hunks: () => hunks,
		reviewOwnsRemovedLines: () => reviewOwnsRemovedLines
	});

	/** Whether a cell's line changed in the way its column shows. */
	function changed(cell: DrawnLine, column: LineSide): boolean {
		return cell.line.kind === CHANGED_IN[column];
	}

	/**
	 * A cell's tint. The mark of lines being written about is added to the
	 * change rather than replacing it, so a line keeps showing what changed on
	 * it while it is written about.
	 */
	function tint(cell: DrawnLine | null, column: LineSide): string {
		if (cell === null) return 'cr-cell-absent';
		const change = changed(cell, column) ? TINTS[column] : '';
		return commenting.isMarked(cell.place) ? `${change} cr-cell-marked` : change;
	}

	function edge(cell: DrawnLine | null, column: LineSide): string {
		if (cell === null) return 'cr-edge';
		if (commenting.isMarked(cell.place)) return 'cr-edge cr-edge-marked';
		return changed(cell, column) ? `cr-edge ${EDGES[column]}` : 'cr-edge';
	}

	/**
	 * The line whose notes a column's half shows under a row, if it has any.
	 * A note sits under the side it is about — in two columns the old and the
	 * new line share a number, and a note in the wrong half says nothing about
	 * which one is meant — so the left half shows notes on removed lines only:
	 * an unchanged line is on the new side, and so are its notes.
	 */
	function notedIn(cell: DrawnLine | null, column: LineSide): LinePlace | null {
		if (cell === null || cell.place.side !== column || !commenting.hasNotes(cell.place)) return null;
		return cell.place;
	}
</script>

<!-- On the window, so a drag let go anywhere — above the sticky header, say — still ends -->
<svelte:window onmouseup={() => commenting.release()} />

<div data-testid="split-view">
	{#each hunks as hunk (hunk.key)}
		<div class="border-b border-base-300">
			<HunkGap
				gap={hunk.gap}
				header={hunk.header}
				onReveal={revealed ? (gap) => revealed.reveal(file.path, gap) : null}
			/>

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
					{#each splitRows(hunk.lines) as row (row.key)}
						{@const leftNotes = notedIn(row.left, 'old')}
						{@const rightNotes = notedIn(row.right, 'new')}
						<tr data-testid="split-row" class="cr-side-del">
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<td
								class="cr-gutter w-12 p-0 text-right select-none {edge(row.left, 'old')} {tint(row.left, 'old')}"
								onmouseenter={() => row.left && commenting.enter(row.left)}
							>
								{#if row.left}
									<!-- One keyboard stop per row: the new side's number, or this
										one when the row has nothing on the new side -->
									<LineGutter drawn={row.left} side="old" stop={row.right === null} {commenting} />
								{/if}
							</td>
							<td
								data-testid="split-old-code"
								class="cr-code-cell border-r border-base-300 px-2 whitespace-pre-wrap {tint(row.left, 'old')}"
							>
								{#if row.left}{@html row.left.markup}{/if}
							</td>

							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<td
								class="cr-gutter cr-side-add w-12 p-0 text-right select-none {edge(row.right, 'new')} {tint(
									row.right,
									'new'
								)}"
								onmouseenter={() => row.right && commenting.enter(row.right)}
							>
								{#if row.right}
									<LineGutter drawn={row.right} side="new" stop {commenting} />
								{/if}
							</td>
							<td
								data-testid="split-new-code"
								class="cr-side-add cr-code-cell px-2 pr-4 whitespace-pre-wrap {tint(row.right, 'new')}"
							>
								{#if row.right}{@html row.right.markup}{/if}
							</td>
						</tr>

						{#if leftNotes || rightNotes}
							<tr>
								<td colspan="2" class="align-top">
									{#if leftNotes}
										<LineNotes {commenting} place={leftNotes} />
									{/if}
								</td>
								<td colspan="2" class="align-top">
									{#if rightNotes}
										<LineNotes {commenting} place={rightNotes} />
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

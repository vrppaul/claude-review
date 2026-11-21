<script lang="ts">
	import type { ClassValue } from 'svelte/elements';
	import { LINE_CODE_ROLE } from '$lib/dom/line-code';
	import { LINE_ROW_ROLE } from '$lib/dom/line-read-from.svelte';
	import type { LinePlace, LineSide } from '$lib/types';
	import LineFailure from '$lib/ui/LineFailure.svelte';
	import type { DrawnLine } from '$lib/utils/drawn-file';
	import { splitRows, type SplitRow } from '$lib/utils/split-rows';
	import type { FileDrawing } from './file-drawing.svelte';
	import HunkGap from './HunkGap.svelte';
	import LineGutter from './LineGutter.svelte';
	import type { Reach } from './line-commenting.svelte';
	import LineNotes from './LineNotes.svelte';

	// The two columns are the two sides, the old on the left: the kind of line each colours as changed
	const CHANGED_IN: Record<LineSide, 'delete' | 'add'> = { old: 'delete', new: 'add' };
	// How a cell is tinted, and how its edge is coloured, when its line changed
	const TINTS: Record<LineSide, string> = { old: 'cr-cell-del', new: 'cr-cell-add' };
	const EDGES: Record<LineSide, string> = { old: 'cr-edge-del', new: 'cr-edge-add' };

	interface Props {
		/** The file made ready to draw, by whoever draws it. */
		drawing: FileDrawing;
	}

	let { drawing }: Props = $props();
	const commenting = $derived(drawing.commenting);
	const naming = $derived(drawing.naming);

	/** Whether a cell's line changed in the way its column shows. */
	function changed(cell: DrawnLine, column: LineSide): boolean {
		return cell.line.kind === CHANGED_IN[column];
	}

	/**
	 * Whether a cell wears the reader's mark: its line is being written
	 * about, or the page took them to it. The line taken to is marked in its
	 * own half alone: a line the change kept stands in both, and is the new
	 * side's.
	 */
	function marked(cell: DrawnLine, column: LineSide): boolean {
		return commenting.isMarked(cell.place) || (cell.place.side === column && drawing.arrivedAt(cell));
	}

	/**
	 * A cell's tint. The reader's mark is added to the change rather than
	 * replacing it, so a line keeps showing what changed on it while it is
	 * written about.
	 */
	function tint(cell: DrawnLine | null, column: LineSide): ClassValue {
		if (cell === null) return 'cr-cell-absent';
		return [changed(cell, column) && TINTS[column], marked(cell, column) && 'cr-cell-marked'];
	}

	/** A cell's edge: the reader's mark outranks the change, as it does across a row. */
	function edge(cell: DrawnLine | null, column: LineSide): ClassValue {
		if (cell === null) return 'cr-edge';
		if (marked(cell, column)) return ['cr-edge', 'cr-edge-marked'];
		return ['cr-edge', changed(cell, column) && EDGES[column]];
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

	/**
	 * How the keyboard reaches a row's left number. The right one is the row's
	 * stop, unless the row has nothing on the right; a removed line facing
	 * the line that replaced it is a line of its own, which Tab reaches; an
	 * unchanged line's left number is the same line as its right one.
	 */
	function leftReach(row: SplitRow): Reach {
		if (row.right === null) return 'row-stop';
		return row.left === row.right ? 'pointer' : 'tab';
	}
</script>

<div data-testid="split-view">
	{#each drawing.hunks() as hunk (hunk.key)}
		<div class="cr-hunk">
			<HunkGap gap={hunk.gap} header={hunk.header} {drawing} />

			<table class="cr-code w-full table-fixed border-collapse font-mono">
				<!-- Fixed layout with both content columns unsized: the two halves
					then split what the gutters leave, so neither side is wider. -->
				<colgroup>
					<col class="w-(--cr-line-number-width)" />
					<col />
					<col class="w-(--cr-line-number-width)" />
					<col />
				</colgroup>
				<tbody>
					{#each splitRows(hunk.lines) as row (row.key)}
						{@const leftNotes = notedIn(row.left, 'old')}
						{@const rightNotes = notedIn(row.right, 'new')}
						<tr data-testid="split-row" data-role={LINE_ROW_ROLE} class="cr-side-del">
							<td
								class={[
									'cr-gutter w-(--cr-line-number-width) p-0 text-right select-none',
									edge(row.left, 'old'),
									tint(row.left, 'old')
								]}
								onmouseenter={() => row.left && commenting.enter(row.left)}
							>
								{#if row.left}
									<LineGutter drawn={row.left} side="old" reach={leftReach(row)} {commenting} />
								{/if}
							</td>
							<td
								data-testid="split-old-code"
								data-role={LINE_CODE_ROLE}
								class={['cr-code-cell border-r border-base-300 px-2 whitespace-pre-wrap', tint(row.left, 'old')]}
								onmousemove={(event) => row.left && naming?.point(event, event.currentTarget, row.left)}
								onmouseleave={(event) => row.left && naming?.point(event, event.currentTarget, row.left)}
								onclick={(event) => row.left && naming?.press(event, event.currentTarget, row.left)}
							>
								{#if row.left}{@html row.left.markup}{/if}
							</td>

							<td
								class={[
									'cr-gutter cr-side-add w-(--cr-line-number-width) p-0 text-right select-none',
									edge(row.right, 'new'),
									tint(row.right, 'new')
								]}
								onmouseenter={() => row.right && commenting.enter(row.right)}
							>
								{#if row.right}
									<LineGutter drawn={row.right} side="new" reach="row-stop" {commenting} />
								{/if}
							</td>
							<td
								data-testid="split-new-code"
								data-role={LINE_CODE_ROLE}
								class={['cr-side-add cr-code-cell px-2 pr-4 whitespace-pre-wrap', tint(row.right, 'new')]}
								onmousemove={(event) => row.right && naming?.point(event, event.currentTarget, row.right)}
								onmouseleave={(event) => row.right && naming?.point(event, event.currentTarget, row.right)}
								onclick={(event) => row.right && naming?.press(event, event.currentTarget, row.right)}
							>
								{#if row.right}{@html row.right.markup}{/if}
							</td>
						</tr>

						<!-- What the checks found failing on the line of the right, under it as its notes are -->
						{#each row.right ? drawing.failuresUnder(row.right.place) : [] as found (found)}
							<tr>
								<td colspan="2"></td>
								<td colspan="2">
									<LineFailure
										check={found.check}
										what={found.failure.what}
										why={found.failure.why}
										outOfDate={found.outOfDate}
										testId="line-failure"
									/>
								</td>
							</tr>
						{/each}

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
	{#if drawing.end}
		<HunkGap gap={drawing.end} header="" {drawing} />
	{/if}
</div>

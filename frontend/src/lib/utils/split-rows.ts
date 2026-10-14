import type { DiffLine } from '$lib/types';
import type { DrawnLine } from '$lib/utils/drawn-file';
import { facingLines, type Run, runsOf } from '$lib/utils/replacements';

/** One row of two columns: the line before on the left, the line after on the right. */
export interface SplitRow {
	/** What the row is known by: the lines on it. */
	key: string;
	/** Null where the change has nothing on that side of the row. */
	left: DrawnLine | null;
	right: DrawnLine | null;
}

/**
 * Lay a hunk out as two columns, before on the left and after on the right.
 *
 * An unchanged line appears on both sides of one row. Removed lines face the
 * lines that replaced them, so a replacement is read across rather than
 * down; whichever side of it is longer leaves the other side of the surplus
 * rows empty.
 */
export function splitRows(lines: DrawnLine[]): SplitRow[] {
	return runsOf(lines).flatMap(rowsOf);
}

function rowsOf(run: Run<DrawnLine>): SplitRow[] {
	if (run.kind === 'kept') return [rowOf(run.line, run.line)];
	return facingLines(run).map(({ removed, added }) => rowOf(removed, added));
}

/** How many rows `splitRows` lays a hunk's lines out in, counted before they are made ready to draw. */
export function splitRowCount(lines: readonly DiffLine[]): number {
	return runsOf(lines.map((line) => ({ line }))).reduce((rows, run) => rows + rowsTaken(run), 0);
}

/** How many rows a run takes in two columns: a kept line one, a replacement as many as its longer side. */
function rowsTaken(run: Run<unknown>): number {
	return run.kind === 'kept' ? 1 : facingLines(run).length;
}

function rowOf(left: DrawnLine | null, right: DrawnLine | null): SplitRow {
	return { key: `${left?.key ?? ''}|${right?.key ?? ''}`, left, right };
}

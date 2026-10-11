import type { DrawnLine } from '$lib/utils/drawn-file';
import { type Run, runsOf } from '$lib/utils/replacements';

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
	const height = Math.max(run.removed.length, run.added.length);
	return Array.from({ length: height }, (_, offset) =>
		rowOf(run.removed.at(offset) ?? null, run.added.at(offset) ?? null)
	);
}

function rowOf(left: DrawnLine | null, right: DrawnLine | null): SplitRow {
	return { key: `${left?.key ?? ''}|${right?.key ?? ''}`, left, right };
}

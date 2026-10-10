import type { DrawnLine } from '$lib/utils/drawn-file';

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
 * An unchanged line appears on both sides of one row. A run of removals is
 * faced with the run of additions that follows it, paired in order, so a
 * replacement is read across rather than down; whichever run is longer leaves
 * the other side of the surplus rows empty.
 */
export function splitRows(lines: DrawnLine[]): SplitRow[] {
	const rows: SplitRow[] = [];
	let index = 0;

	while (index < lines.length) {
		if (lines[index].line.kind === 'context') {
			rows.push(rowOf(lines[index], lines[index]));
			index += 1;
			continue;
		}

		const removals: DrawnLine[] = [];
		while (index < lines.length && lines[index].line.kind === 'delete') {
			removals.push(lines[index]);
			index += 1;
		}

		const additions: DrawnLine[] = [];
		while (index < lines.length && lines[index].line.kind === 'add') {
			additions.push(lines[index]);
			index += 1;
		}

		const height = Math.max(removals.length, additions.length);
		for (let offset = 0; offset < height; offset += 1) {
			rows.push(rowOf(removals.at(offset) ?? null, additions.at(offset) ?? null));
		}
	}

	return rows;
}

function rowOf(left: DrawnLine | null, right: DrawnLine | null): SplitRow {
	return { key: `${left?.key ?? ''}|${right?.key ?? ''}`, left, right };
}

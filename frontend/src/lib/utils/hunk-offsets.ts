import type { DiffHunk } from '$lib/types';

/**
 * Where each hunk's first line falls among a file's lines counted end to end.
 *
 * A line is told apart from every other in the file by that one number, so
 * the views can say which line a comment opens under without the hunk.
 */
export function hunkOffsets(hunks: DiffHunk[]): number[] {
	const offsets: number[] = [];
	let linesBefore = 0;
	for (const hunk of hunks) {
		offsets.push(linesBefore);
		linesBefore += hunk.lines.length;
	}
	return offsets;
}

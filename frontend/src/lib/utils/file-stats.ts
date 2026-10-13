import type { DiffFile } from '$lib/types';

/** How much changed: the lines added, and the lines removed. */
export interface FileStats {
	additions: number;
	deletions: number;
}

/** How much a file, or a piece of one, changes: the lines its hunks add and remove. */
export function fileStats(file: DiffFile): FileStats {
	let additions = 0;
	let deletions = 0;
	for (const hunk of file.hunks) {
		for (const line of hunk.lines) {
			if (line.kind === 'add') additions++;
			else if (line.kind === 'delete') deletions++;
		}
	}
	return { additions, deletions };
}

/** How much several pieces change together. */
export function totalOf(pieces: readonly FileStats[]): FileStats {
	return {
		additions: pieces.reduce((sum, piece) => sum + piece.additions, 0),
		deletions: pieces.reduce((sum, piece) => sum + piece.deletions, 0)
	};
}

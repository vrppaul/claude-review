import type { FileLines, ThreadOnLines } from '$lib/anchors/views';
import type { DiffFile, LineSide, Thread } from '$lib/types';

/**
 * Whether a thread on these lines has a row to hang on in the diff as it is drawn.
 *
 * A narrower base leaves out the files it has nothing to say about, and the
 * hunks of the files it keeps. A thread whose lines are not among them is
 * not lost — it is anchored to the review's own diff, which has not moved —
 * but there is nowhere to draw it here, so it is counted and said out loud
 * instead.
 *
 * Removed lines are the second way out. Their numbers belong to whatever is
 * on the left, and a narrower base puts something else there: a thread on
 * old line 17 would be drawn against whichever line now sits at 17. So with
 * `removedLines` off, the old side is not drawn at all.
 */
export function isDrawn(
	lines: FileLines,
	files: DiffFile[],
	{ removedLines = true }: { removedLines?: boolean } = {}
): boolean {
	if (!sideIsDrawn(lines.side, removedLines)) return false;

	const file = files.find((candidate) => candidate.path === lines.file);
	if (!file) return false;

	return file.hunks.some((hunk) =>
		hunk.lines.some((line) => (lines.side === 'old' ? line.old_number : line.new_number) === lines.end_line)
	);
}

/**
 * Whether what hangs on a side is drawn at all — a thread, a comment being
 * written: what hangs on removed lines is not, under a narrower base.
 */
export function sideIsDrawn(side: LineSide, removedLines: boolean): boolean {
	return side !== 'old' || removedLines;
}

/** The threads on one file the diff does not hold. */
export interface ThreadsOffTheDiff {
	file: string;
	threads: Thread[];
}

/**
 * The threads on files the diff does not hold — put back as they were, say,
 * and the diff taken again: no file is drawn for them to hang in. By file,
 * in the order the threads stand.
 */
export function threadsOffTheDiff(onLines: readonly ThreadOnLines[], files: readonly DiffFile[]): ThreadsOffTheDiff[] {
	const drawn = new Set(files.map((file) => file.path));
	const byFile = Map.groupBy(
		onLines.filter(({ lines }) => !drawn.has(lines.file)),
		({ lines }) => lines.file
	);
	return [...byFile].map(([file, held]) => ({ file, threads: held.map(({ thread }) => thread) }));
}

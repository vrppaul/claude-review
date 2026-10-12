import type { FileLines, ThreadOnLines } from '$lib/anchors/views';
import type { DiffFile, DiffLine, LineSide, Thread } from '$lib/types';

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

/** A thread as it stands in a file the diff holds: the file's place among the files, and the row it hangs under. */
interface Standing {
	thread: Thread;
	filePlace: number;
	row: number;
}

/** A file's rows as the diff holds them, and the file's place among the files. */
interface FileRows {
	place: number;
	rows: DiffLine[];
}

/** A line's number on one side; null for a line that is not on it. */
function numberOn(side: LineSide, line: DiffLine): number | null {
	return side === 'old' ? line.old_number : line.new_number;
}

/**
 * The row a thread's lines hang under, among a file's rows: their last line's
 * own, or, that line not among them — read in from between two changes —
 * the row it would stand before. A row with no number on the thread's side,
 * an added line for a thread on removed ones, is never it.
 */
function rowOf(lines: FileLines, rows: readonly DiffLine[]): number {
	const at = rows.findIndex((line) => (numberOn(lines.side, line) ?? Number.NEGATIVE_INFINITY) >= lines.end_line);
	return at === -1 ? rows.length : at;
}

/** Where a thread stands, if its file is one the diff holds. */
function standingOf({ thread, lines }: ThreadOnLines, held: ReadonlyMap<string, FileRows>): Standing[] {
	const file = held.get(lines.file);
	return file ? [{ thread, filePlace: file.place, row: rowOf(lines, file.rows) }] : [];
}

/**
 * The threads in the order they stand on the diff: those on files it does
 * not hold first, as they are drawn above it, then file by file in the
 * diff's order, each file down its rows.
 */
export function inDiffOrder(onLines: readonly ThreadOnLines[], files: readonly DiffFile[]): Thread[] {
	const held = new Map(
		files.map((file, place) => [file.path, { place, rows: file.hunks.flatMap((hunk) => hunk.lines) }])
	);
	const onFiles = onLines
		.flatMap((onLine) => standingOf(onLine, held))
		.sort((one, other) => one.filePlace - other.filePlace || one.row - other.row);
	const above = threadsOffTheDiff(onLines, files).flatMap(({ threads }) => threads);
	return [...above, ...onFiles.map(({ thread }) => thread)];
}

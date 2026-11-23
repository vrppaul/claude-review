import { type Numbering, sideIsTheReviews } from '$lib/anchors/numbering';
import type { FileLines, ThreadOnLines } from '$lib/anchors/views';
import type { DiffFile, DiffLine, LineSide, Thread } from '$lib/types';

/** A line's number on one side; null for a line that is not on it. */
function numberOn(side: LineSide, line: DiffLine): number | null {
	return side === 'old' ? line.old_number : line.new_number;
}

/**
 * Whether a file as it is drawn — a file of the diff, or a piece cut out of
 * one — has a row for a thread on these lines to hang on: it is their file,
 * shows their last line, and numbers that side as the review does.
 */
export function fileDraws(file: DiffFile, lines: FileLines, numbering: Numbering): boolean {
	if (file.path !== lines.file || !sideIsTheReviews(lines.side, numbering)) return false;

	return file.hunks.some((hunk) => hunk.lines.some((line) => numberOn(lines.side, line) === lines.end_line));
}

/**
 * Whether a thread on these lines has a row to hang on among files as they
 * are drawn, their lines numbered as `numbering` says.
 *
 * A narrower base leaves out the files it has nothing to say about, and the
 * hunks of the files it keeps. A thread whose lines are not among them is
 * not lost — it is anchored to the review's own diff, which has not moved —
 * but there is nowhere to draw it here, so it is counted and said out loud
 * instead. Nor is there on a side whose numbers are not the review's own.
 */
export function isDrawn(lines: FileLines, files: DiffFile[], numbering: Numbering): boolean {
	return files.some((file) => fileDraws(file, lines, numbering));
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

/**
 * The rows one section of a view draws — a file of the diff, a piece of a
 * story — and the section's place among those the view draws.
 */
export interface DrawnRows {
	place: number;
	rows: readonly DiffLine[];
}

/** A thread as it stands in what a view draws: the place of the section that draws it, and the row it hangs under there. */
interface Standing {
	thread: Thread;
	place: number;
	row: number;
}

/**
 * The row a thread's lines hang under, among the rows a section draws: their
 * last line's own, or, that line not among them — read in from between two
 * changes — the row it would stand before. A row with no number on the
 * thread's side, an added line for a thread on removed ones, is never it.
 */
function rowOf(lines: FileLines, rows: readonly DiffLine[]): number {
	const at = rows.findIndex((line) => (numberOn(lines.side, line) ?? Number.NEGATIVE_INFINITY) >= lines.end_line);
	return at === -1 ? rows.length : at;
}

/** Where a thread stands, if a section draws it. */
function standingOf({ thread, lines }: ThreadOnLines, drawnIn: (lines: FileLines) => DrawnRows | null): Standing[] {
	const drawn = drawnIn(lines);
	return drawn === null ? [] : [{ thread, place: drawn.place, row: rowOf(lines, drawn.rows) }];
}

/**
 * The threads in the order they stand in what a view draws: section by
 * section in the view's own order, each section down its rows. A thread
 * `drawnIn` finds no section for is left out.
 */
export function inDrawnOrder(
	onLines: readonly ThreadOnLines[],
	drawnIn: (lines: FileLines) => DrawnRows | null
): Thread[] {
	return onLines
		.flatMap((onLine) => standingOf(onLine, drawnIn))
		.sort((one, other) => one.place - other.place || one.row - other.row)
		.map(({ thread }) => thread);
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
	const above = threadsOffTheDiff(onLines, files).flatMap(({ threads }) => threads);
	return [...above, ...inDrawnOrder(onLines, (lines) => held.get(lines.file) ?? null)];
}

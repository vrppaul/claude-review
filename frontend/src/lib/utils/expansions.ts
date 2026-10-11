/**
 * What the diff left out around a file's hunks, and reading it in: up from
 * the hunk below a gap, down from the hunk above it, or the whole of it at
 * once, as GitHub does.
 */

import type { DiffFile, DiffHunk, DiffLine } from '$lib/types';

/**
 * How many lines one step up or down reads: GitHub's step, enough to see
 * the function a change sits in, few enough that one click does not bury
 * the change under context. A gap no longer than this is read whole.
 */
export const EXPAND_STEP = 20;

/** What the gap below the last hunk is known by: the end of the file. Hunks are known by numbers, never by this. */
const END_OF_FILE = 'end';

/** Which way a read widens a gap: up from the hunk below it, down from the hunk above it, or across the whole of it. */
export type Widening = 'up' | 'down' | 'all';

/** Lines of a file, the first and the last both included. */
interface LineWindow {
	start: number;
	end: number;
}

/** Where lines read into a gap are drawn: above the hunk below it, or below the hunk above it. */
interface Landing {
	/** The hunk they are drawn against, by what it is known by. */
	hunk: string;
	side: 'above' | 'below';
}

/**
 * The unchanged lines the diff left out above a hunk, between two, or below
 * the last, as far as they are still hidden.
 */
export interface ContextGap {
	/** What the gap is known by while its lines are read: the hunk below it, or the end of the file. */
	key: string;
	/** The hunk above it, by what it is known by; null for the gap above the first. */
	above: string | null;
	/** The hunk below it; null for the gap below the last. */
	below: string | null;
	/** The first line hidden. */
	first: number;
	/** The last line hidden; null below the last hunk until a read has said how long the file is. */
	last: number | null;
	/** How far the old numbering runs behind the new one across the gap. */
	oldOffset: number;
}

/** A read into a gap: the lines it asks for, and where they are drawn once read. */
export interface GapRead {
	/** The gap it reads into, by its key: one read of a gap at a time. */
	gap: string;
	window: LineWindow;
	landing: Landing;
	/** How far the old numbering runs behind the new one where the lines land. */
	oldOffset: number;
}

/** Lines read in around one file's hunks, and how long the file is once a read has said. */
export interface RevealedLines {
	/** By the hunk they are drawn above. */
	above: ReadonlyMap<string, DiffLine[]>;
	/** By the hunk they are drawn below. */
	below: ReadonlyMap<string, DiffLine[]>;
	/** How many lines the file has; null until a read has said. */
	length: number | null;
}

/**
 * What a hunk is known by within its diff: where it starts on each side.
 *
 * Its place in the file's list of hunks is no name for it: another reading
 * of the same file — a story step cut out of it — numbers its hunks afresh.
 * Git's hunks start further down on both sides, one after the other.
 */
export function hunkKey(hunk: DiffHunk): string {
	return `${hunk.old_start}:${hunk.new_start}`;
}

/** How many lines a gap hides; null where that is not known yet. */
export function hiddenIn(gap: ContextGap): number | null {
	return gap.last === null ? null : Math.max(0, gap.last - gap.first + 1);
}

/**
 * The gap above a hunk as it is drawn, below the hunk drawn above it — the
 * top of the file when there is none.
 *
 * Revealed lines are drawn inside the hunks beside them, so the gap is what
 * still lies between one hunk's last line and the next one's first: it
 * closes as lines are revealed, with nothing kept beside the hunks to count.
 */
export function gapAbove(hunk: DiffHunk, above: DiffHunk | undefined): ContextGap {
	return {
		key: hunkKey(hunk),
		above: above ? hunkKey(above) : null,
		below: hunkKey(hunk),
		first: above ? lastNewLine(above) + 1 : 1,
		last: firstNewLine(hunk) - 1,
		oldOffset: hunk.old_start - hunk.new_start
	};
}

/**
 * The gap below the last hunk as it is drawn, up to the end of the file once
 * a read has said where that is; null where nothing can lie below it.
 *
 * Until a read says how long the file is, it may go on below — unless the
 * hunk ends on a line the change touched: the diff carries the unchanged
 * lines after a change wherever the file has them, so a hunk that ends on a
 * change ends the file.
 */
export function gapBelow(last: DiffHunk, length: number | null): ContextGap | null {
	if (length === null && last.lines.at(-1)?.kind !== 'context') return null;
	return {
		key: END_OF_FILE,
		above: hunkKey(last),
		below: null,
		first: lastNewLine(last) + 1,
		last: length,
		oldOffset: lastOldLine(last) - lastNewLine(last)
	};
}

/**
 * The read a widening makes of a gap; null where it reads nothing there.
 *
 * @param longestRead the most lines one read hands back: a read asks for no
 *   more, so every line it asks for comes back, next to the lines it was read from
 */
export function readOf(gap: ContextGap, widening: Widening, longestRead: number): GapRead | null {
	if (hiddenIn(gap) === 0) return null;
	return READS[widening](gap, longestRead);
}

/** How many lines a read asks for. */
export function sizeOf(read: GapRead): number {
	return read.window.end - read.window.start + 1;
}

/** The lines just above the hunk below the gap, read up from it. */
function readUp(gap: ContextGap): GapRead | null {
	if (gap.below === null || gap.last === null) return null;
	const window = { start: Math.max(gap.first, gap.last - EXPAND_STEP + 1), end: gap.last };
	return { gap: gap.key, window, landing: { hunk: gap.below, side: 'above' }, oldOffset: gap.oldOffset };
}

/** The lines just below the hunk above the gap, read down from it: as far as the file goes, where its end is not known. */
function readDown(gap: ContextGap): GapRead | null {
	if (gap.above === null) return null;
	const furthest = gap.first + EXPAND_STEP - 1;
	const window = { start: gap.first, end: gap.last === null ? furthest : Math.min(gap.last, furthest) };
	return { gap: gap.key, window, landing: { hunk: gap.above, side: 'below' }, oldOffset: gap.oldOffset };
}

/**
 * Every hidden line, as many as one read hands back: down from the hunk
 * above, or up to the first hunk where none is above. Unknown where the gap
 * ends, it reads nothing.
 */
function readAll(gap: ContextGap, longestRead: number): GapRead | null {
	if (gap.last === null) return null;
	if (gap.above !== null) {
		const window = { start: gap.first, end: Math.min(gap.last, gap.first + longestRead - 1) };
		return { gap: gap.key, window, landing: { hunk: gap.above, side: 'below' }, oldOffset: gap.oldOffset };
	}
	if (gap.below === null) return null;
	const window = { start: Math.max(gap.first, gap.last - longestRead + 1), end: gap.last };
	return { gap: gap.key, window, landing: { hunk: gap.below, side: 'above' }, oldOffset: gap.oldOffset };
}

/** Each widening's read: up from the hunk below, down from the hunk above, or the whole gap. */
const READS: Record<Widening, (gap: ContextGap, longestRead: number) => GapRead | null> = {
	up: readUp,
	down: readDown,
	all: readAll
};

/**
 * The file as it should be drawn, with revealed lines folded into the hunks.
 *
 * Revealed lines are unchanged context, so putting them inside the hunk they
 * sit beside means line numbering, highlighting and comment anchoring all
 * treat them like any other context line, with nothing to special-case.
 */
export function withRevealed(file: DiffFile, revealed: RevealedLines): DiffFile {
	if (revealed.above.size === 0 && revealed.below.size === 0) return file;

	return { ...file, hunks: file.hunks.map((hunk) => withLinesBeside(hunk, revealed)) };
}

/** A hunk with the lines revealed above it before its own, and those revealed below it after, if any were. */
function withLinesBeside(hunk: DiffHunk, revealed: RevealedLines): DiffHunk {
	const key = hunkKey(hunk);
	const above = revealed.above.get(key) ?? [];
	const below = revealed.below.get(key) ?? [];
	if (above.length === 0 && below.length === 0) return hunk;
	return { ...hunk, lines: [...above, ...hunk.lines, ...below] };
}

/**
 * Turn fetched text into context lines numbered from `start`.
 *
 * `oldOffset` is how far the old numbering runs behind the new one at this
 * point in the file, so a revealed line carries a number in both gutters
 * like every other context line around it.
 */
export function toContextLines(start: number, lines: string[], oldOffset: number): DiffLine[] {
	return lines.map((content, offset) => ({
		kind: 'context' as const,
		old_number: start + offset + oldOffset,
		new_number: start + offset,
		content
	}));
}

/** The new side's first line in a hunk; for a hunk with none there, where it would be. */
function firstNewLine(hunk: DiffHunk): number {
	return hunk.lines.find((line) => line.new_number !== null)?.new_number ?? hunk.new_start;
}

/** The new side's last line in a hunk; for a hunk with none there, the line before it. */
function lastNewLine(hunk: DiffHunk): number {
	const last = hunk.lines.findLast((line) => line.new_number !== null);
	return last?.new_number ?? hunk.new_start - 1;
}

/** The old side's last line in a hunk; for a hunk with none there, the line before it. */
function lastOldLine(hunk: DiffHunk): number {
	const last = hunk.lines.findLast((line) => line.old_number !== null);
	return last?.old_number ?? hunk.old_start - 1;
}

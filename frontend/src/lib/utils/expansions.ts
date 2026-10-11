import type { DiffFile, DiffHunk, DiffLine } from '$lib/types';

/** How many lines one click reveals. */
export const EXPAND_STEP = 20;

/** A gap this small is not worth revealing a piece at a time. */
const EXPAND_ALL_BELOW = 60;

/** Lines of a file, the first and the last both included. */
interface LineWindow {
	start: number;
	end: number;
}

/** The unchanged lines the diff left out above a hunk, as far as they are still hidden. */
export interface ContextGap {
	/** The hunk below the gap, by what it is known by. */
	hunk: string;
	/** How many lines are hidden. */
	hidden: number;
	/** The lines one click asks for: the ones just above the hunk. Null when nothing is hidden. */
	next: LineWindow | null;
	/** How far the old numbering runs behind the new one at the hunk. */
	oldOffset: number;
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

/**
 * The gap above a hunk as it is drawn, below the hunk drawn above it — the
 * top of the file when there is none.
 *
 * Revealed lines are drawn inside the hunk below them, so the gap is what
 * still lies between one hunk's last line and the next one's first: it
 * closes as lines are revealed, with nothing kept beside the hunks to count.
 */
export function gapAbove(hunk: DiffHunk, above: DiffHunk | undefined): ContextGap {
	const firstHidden = above ? lastNewLine(above) + 1 : 1;
	const lastHidden = firstNewLine(hunk) - 1;
	const hidden = Math.max(0, lastHidden - firstHidden + 1);
	const wanted = hidden <= EXPAND_ALL_BELOW ? hidden : EXPAND_STEP;
	return {
		hunk: hunkKey(hunk),
		hidden,
		next: hidden === 0 ? null : { start: lastHidden - wanted + 1, end: lastHidden },
		oldOffset: hunk.old_start - hunk.new_start
	};
}

/**
 * The file as it should be drawn, with revealed lines folded into the hunks.
 *
 * Revealed lines are unchanged context, so putting them inside the hunk they
 * sit above means line numbering, highlighting and comment anchoring all
 * treat them like any other context line, with nothing to special-case.
 */
export function withRevealed(file: DiffFile, revealed: ReadonlyMap<string, DiffLine[]>): DiffFile {
	if (revealed.size === 0) return file;

	return { ...file, hunks: file.hunks.map((hunk) => withLinesAbove(hunk, revealed)) };
}

/** A hunk with the lines revealed above it put before its own, if any were. */
function withLinesAbove(hunk: DiffHunk, revealed: ReadonlyMap<string, DiffLine[]>): DiffHunk {
	const above = revealed.get(hunkKey(hunk));
	if (!above || above.length === 0) return hunk;
	return { ...hunk, lines: [...above, ...hunk.lines] };
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

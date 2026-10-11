/**
 * A file's lines made ready to draw, once, for whichever layout draws them:
 * each line with its place, the row it is known by, and its markup.
 *
 * Both layouts draw the same lines, and a row is known by the line's place
 * rather than its position: lines revealed above a hunk move every row below
 * them down, and a row known by its position would then be another line,
 * taking the threads and the comment field under it along.
 */

import type { DiffFile, DiffHunk, DiffLine, LinePlace } from '$lib/types';
import { type ContextGap, gapAbove, hunkKey } from '$lib/utils/expansions';
import { type HighlightedLine, highlightHunk } from '$lib/utils/highlight';
import { withWordMarks } from '$lib/utils/word-diff';

/**
 * The number of a line that has none on its own side. The parser numbers
 * every line on its side; the wire type cannot say so, and nothing hangs on
 * a line numbered this.
 */
export const NO_NUMBER = 0;

/** A line as it is drawn: its text highlighted, with what changed inside a replaced line marked. */
export interface DrawnLine extends HighlightedLine {
	/** Where it is: what a comment on it hangs on. */
	place: LinePlace;
	/** What its row is known by among the file's rows: its place. */
	key: string;
}

/** A hunk as it is drawn: what the diff left out above it, and its lines. */
export interface DrawnHunk {
	/** What it is known by: where it starts on each side. */
	key: string;
	header: string;
	gap: ContextGap;
	lines: DrawnLine[];
}

/** Where a line is: on the old side if the change removed it, on the new side otherwise. */
function placeOf(line: DiffLine): LinePlace {
	if (line.kind === 'delete') return { side: 'old', number: line.old_number ?? NO_NUMBER };
	return { side: 'new', number: line.new_number ?? NO_NUMBER };
}

/** Whether two places are the same line. */
export function samePlace(one: LinePlace, other: LinePlace): boolean {
	return one.side === other.side && one.number === other.number;
}

/** What a place is known by wherever lines are looked up by where they are. */
export function placeKey(place: LinePlace): string {
	return `${place.side}:${place.number}`;
}

/**
 * A file's hunks, ready to draw.
 *
 * @param file the file as shown, revealed lines folded into its hunks
 * @param language what to highlight it as, if anything
 * @param marksWords whether what changed inside a replaced line is marked: in a diff, where lines are replaced
 */
export function drawnHunks(file: DiffFile, language: string | null, marksWords: boolean): DrawnHunk[] {
	return file.hunks.map((hunk, index) => drawnHunk(hunk, file.hunks[index - 1], language, marksWords));
}

/** A hunk ready to draw, below the hunk drawn above it, if any is. */
function drawnHunk(
	hunk: DiffHunk,
	above: DiffHunk | undefined,
	language: string | null,
	marksWords: boolean
): DrawnHunk {
	const lines = highlightHunk(hunk.lines, language).map(drawnLine);
	return {
		key: hunkKey(hunk),
		header: hunk.header,
		gap: gapAbove(hunk, above),
		lines: marksWords ? withWordMarks(lines) : lines
	};
}

function drawnLine(highlighted: HighlightedLine): DrawnLine {
	const place = placeOf(highlighted.line);
	return { ...highlighted, place, key: placeKey(place) };
}

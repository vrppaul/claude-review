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
import { type ContextGap, gapsOf, hunkKey } from '$lib/utils/expansions';
import { highlightFile } from '$lib/utils/highlight';
import { applyWordMarks } from '$lib/utils/word-diff';

/**
 * The number of a line that has none on its own side. The parser numbers
 * every line on its side; the wire type cannot say so, and nothing hangs on
 * a line numbered this.
 */
export const NO_NUMBER = 0;

/** A line as it is drawn. */
export interface DrawnLine {
	line: DiffLine;
	/** Where it is: what a comment on it hangs on. */
	place: LinePlace;
	/** What its row is known by among the file's rows. */
	key: string;
	/** Its text highlighted, with what changed inside a replaced line marked. */
	markup: string;
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

/**
 * A file's hunks, ready to draw.
 *
 * @param file the file as shown, revealed lines folded into its hunks
 * @param language what to highlight it as, if anything
 * @param marksWords whether what changed inside a replaced line is marked: in a diff, where lines are replaced
 */
export function drawnHunks(file: DiffFile, language: string | null, marksWords: boolean): DrawnHunk[] {
	const markup = highlightFile(file, language);
	const gaps = gapsOf(file.hunks);
	return file.hunks.map((hunk, index) =>
		drawnHunk(hunk, gaps[index], marksWords ? applyWordMarks(hunk.lines, markup[index]) : markup[index])
	);
}

function drawnHunk(hunk: DiffHunk, gap: ContextGap, markup: string[]): DrawnHunk {
	return {
		key: hunkKey(hunk),
		header: hunk.header,
		gap,
		lines: hunk.lines.map((line, index) => drawnLine(line, markup[index]))
	};
}

function drawnLine(line: DiffLine, markup: string): DrawnLine {
	const place = placeOf(line);
	return { line, place, key: `${place.side}:${place.number}`, markup };
}

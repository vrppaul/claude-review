/**
 * Words of a line of code, and where they stand in it as the review counts.
 *
 * The review counts a line's columns in characters, where the browser's
 * strings count UTF-16 units: a character past the first plane, an emoji
 * say, is two units and one column. What is drawn on the page is found by
 * units; what is asked of the review, or said by it, is in columns.
 */

import type { TextRange } from '$lib/utils/markup-marks';

// A word as the review reads one where no grammar reads the line: letters, digits and underscores
const WORDS = /[\p{L}\p{N}_]+/gu;
// A word's last character, whole: one past the first plane is two units
const LAST_CHARACTER = /.$/u;

/** A word of a line by its units, and the character of it the caret stands at or after. */
export interface WordAtCaret extends TextRange {
	/** Where the character pressed begins: the one after the caret, or at a word's end the one before it. */
	pressed: number;
}

/**
 * The word a caret between two characters of a line touches, if any: the
 * one the character after it is in, or else the one it ends. A pointer over
 * the right half of a word's last letter puts the caret past it, and the
 * reader pressed the word all the same.
 */
export function wordAtCaret(text: string, caret: number): WordAtCaret | null {
	for (const match of text.matchAll(WORDS)) {
		const start = match.index;
		const end = start + match[0].length;
		if (start <= caret && caret < end) return { start, end, pressed: caret };
		if (caret === end) return { start, end, pressed: start + match[0].search(LAST_CHARACTER) };
	}
	return null;
}

/** The column a place of a line stands at: the characters before it. */
export function columnOf(text: string, offset: number): number {
	return Array.from(text.slice(0, offset)).length;
}

/** Where a name at a column of a line stands in it, in units. */
export function stretchOfName(text: string, column: number, name: string): TextRange {
	const start = Array.from(text).slice(0, column).join('').length;
	return { start, end: start + name.length };
}

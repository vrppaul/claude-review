/**
 * Whose numbers the lines of a drawing carry.
 *
 * A thread hangs on a line by its number, and a comment is written against
 * one: both mean a line of the review's own diff as it stands. Not every
 * drawing is of that diff. A narrower base puts its own lines on the left,
 * so a removed line's number there is the base's: a thread on old line 17
 * would be drawn against whichever line the base has at 17. What hangs on a
 * line's number, or is written against it, is drawn and taken only where
 * the number is the review's own.
 */

import type { LineSide } from '$lib/types';

/** Whose numbering a drawing's lines are in: the review's own diff's, or a narrower base's on its left. */
export type Numbering = 'the-reviews' | 'a-narrower-bases';

// Under each numbering, the sides whose numbers are somebody else's, and why
// nothing is written on a line there. A side not named is the review's own.
const SOMEBODY_ELSES: Record<Numbering, Partial<Record<LineSide, string>>> = {
	'the-reviews': {},
	'a-narrower-bases': { old: 'A removed line belongs to the base on screen. Show the whole diff to write here.' }
};

/** Why a side's line numbers are not the review's own in a drawing numbered so, in words; null where they are. */
export function whyNotTheReviews(side: LineSide, numbering: Numbering): string | null {
	return SOMEBODY_ELSES[numbering][side] ?? null;
}

/** Whether a side's line numbers are the review's own: what hangs on them is drawn, and a comment is taken there. */
export function sideIsTheReviews(side: LineSide, numbering: Numbering): boolean {
	return whyNotTheReviews(side, numbering) === null;
}

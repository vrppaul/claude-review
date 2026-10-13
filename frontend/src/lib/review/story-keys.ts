/**
 * What each place of a story is known by on the page: its parts — the
 * overview, each chapter, what it leaves out — and the sections that draw
 * its pieces.
 *
 * A place is known by what it is, never by where the story happens to put
 * it. A chapter by its id, under a word no other part begins with, so no id
 * an agent chooses is another part's key. A step's section by its file and
 * the first line it tells, which no two steps share since the review
 * refuses a story that tells a line twice; the section of what is left out
 * of a file by that file, which is left out once. So a place is the same
 * place when the story is told again in another order.
 */

import type { LeftOut, ToldChapter, ToldStep } from '$lib/types';

// What stands between the halves of a key
const KEY_SEPARATOR = ':';
// What the key of a chapter's part begins with, and the key of a step's section
const CHAPTER = 'chapter';
const STEP = 'step';
// What a story leaves out: the key of that part, and what the key of each of its sections begins with
const LEFT_OUT = 'left-out';

/** What the overview's part of the page is known by. */
export const OVERVIEW_PART = 'overview';

/** What the part that draws what no step tells is known by. */
export const LEFT_OUT_PART = LEFT_OUT;

/** What a chapter's part of the page is known by: its id. */
export function chapterPartKey(chapter: ToldChapter): string {
	return [CHAPTER, chapter.id].join(KEY_SEPARATOR);
}

/** What a step's section is known by: its file, and the first of the lines it tells. */
export function stepSectionKey(step: ToldStep): string {
	return [STEP, step.file, step.lines.first].join(KEY_SEPARATOR);
}

/** What the section of what a story leaves out of a file is known by: the file. */
export function leftOutSectionKey(left: LeftOut): string {
	return [LEFT_OUT, left.piece.path].join(KEY_SEPARATOR);
}

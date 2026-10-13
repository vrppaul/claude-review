/**
 * How a story's parts are numbered and named on the page, said one way
 * wherever they are said: in a chapter's heading, beside a step, in what the
 * overview says a decision leads to.
 */

import type { ToldChapter, ToldStep } from '$lib/types';

// What joins the first line of a step to its last, and a chapter's number to a step's
const RANGE_DASH = '–';
const NUMBER_SEPARATOR = '.';
// The number the first of anything in a story goes by: chapters and steps are counted from one
const FIRST_NUMBER = 1;
// What a step and a chapter are called before their numbers: at the head of a heading, and inside a sentence
const A_STEP = 'Step';
const A_CHAPTER = 'chapter';

/** The lines a step tells: the first and the last, both among them. */
type StepLines = ToldStep['lines'];

/** A chapter's number, by its place among the chapters. */
export function chapterNumber(chapterPlace: number): number {
	return chapterPlace + FIRST_NUMBER;
}

/** A step as the story numbers it: its chapter's number, then its own among the chapter's steps. */
export function stepNumber(chapterPlace: number, stepPlace: number): string {
	return `${chapterNumber(chapterPlace)}${NUMBER_SEPARATOR}${stepPlace + FIRST_NUMBER}`;
}

/** A step's lines as the head of its piece says them: "42", or "42–47". */
export function linesSaid({ first, last }: StepLines): string {
	return first === last ? String(first) : `${first}${RANGE_DASH}${last}`;
}

/** A step as its heading names it to whoever cannot see where it stands: "Step 1.2". */
export function stepNamed(number: string): string {
	return `${A_STEP} ${number}`;
}

/**
 * The chapter something leads to, as the reader knows it: by its number.
 * The review refuses a story that leads to a chapter it does not have.
 */
export function chapterNamed(chapters: readonly ToldChapter[], id: string): string {
	return `${A_CHAPTER} ${chapterNumber(chapters.findIndex((chapter) => chapter.id === id))}`;
}

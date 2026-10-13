/**
 * How a story's parts are numbered, named and counted on the page, said one
 * way wherever they are said: in a chapter's heading, beside a step, in the
 * head of a piece, in what the overview says a decision leads to.
 */

import type { ToldChapter, ToldStep } from '$lib/types';
import { counted, type CountedWords, FILES, wordsFor } from '$lib/utils/words';

// What joins the first line of a step to its last, and a chapter's number to a step's
const RANGE_DASH = '–';
const NUMBER_SEPARATOR = '.';
// The number the first of anything in a story goes by: chapters and steps are counted from one
const FIRST_NUMBER = 1;
// What a step and a chapter are called before their numbers: at the head of a heading, and inside a sentence
const A_STEP = 'Step';
const A_CHAPTER = 'chapter';
// And a chapter where the words begin with it, with what stands between its number and its title
const CHAPTER_FIRST = 'Chapter';
const BEFORE_A_TITLE = ': ';
// What chapters are called before their numbers, of one and of several
const CHAPTERS: CountedWords = { one: A_CHAPTER, many: 'chapters' };
// What steps are called where they are counted, and one of them inside a sentence
const STEPS: CountedWords = { one: 'step', many: 'steps' };
// What stands between the two counts of a chapter's head
const BETWEEN_COUNTS = ' · ';
// What stands between the numbers of several chapters
const BETWEEN_NUMBERS = ', ';
// How a file says that other chapters tell it too, before it names them
const ALSO_IN = 'also in';
// What is said of a part, or of some of the chapters, the reader has read through
const READ = 'read';

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

/** What the overview's part of the page is called, to whoever goes through the page by its parts. */
export const THE_OVERVIEW = 'Overview';

/** What the part that draws what no step tells is called, in its heading and by its part of the page. */
export const NOT_IN_THE_STORY = 'Not in the story';

/** A chapter by its number, where the words begin with it, as a way to it says where it leads: "Chapter 2". */
export function chapterByNumber(place: number): string {
	return `${CHAPTER_FIRST} ${chapterNumber(place)}`;
}

/** What a chapter's part of the page is called: "Chapter 2: The end". */
export function chapterEntitled(place: number, title: string): string {
	return `${chapterByNumber(place)}${BEFORE_A_TITLE}${title}`;
}

/** Which of its chapter's steps a step is, as the bar a chapter is read under says: "step 2 of 5". */
export function stepAmong(stepPlace: number, steps: number): string {
	return `${STEPS.one} ${stepPlace + FIRST_NUMBER} of ${steps}`;
}

/** What a part is called in the contents once the reader has read it through: "Chapter 2: The end, read". */
export function calledOnceRead(called: string): string {
	return `${called}, ${READ}`;
}

/**
 * How many chapters a story has, as the head of its contents says: "5
 * chapters", and once the reader has read any of them through, "1 of 5 read".
 */
export function chaptersCounted(chapters: number, read: number): string {
	return read === 0 ? counted(chapters, CHAPTERS) : `${read} of ${chapters} ${READ}`;
}

/** How much a chapter tells, as its head says: "3 files · 4 steps". */
export function filesAndSteps(files: number, steps: number): string {
	return [counted(files, FILES), counted(steps, STEPS)].join(BETWEEN_COUNTS);
}

/** The numbers of some chapters, by their places: "1", "1, 4". */
function numbersOf(places: readonly number[]): string {
	return places.map(chapterNumber).join(BETWEEN_NUMBERS);
}

/**
 * The other chapters that tell the file of a piece, by their places, as its
 * head says them: "also in chapter 1", "also in chapters 1, 4".
 */
export function alsoInChapters(places: readonly number[]): string {
	return `${ALSO_IN} ${wordsFor(places.length, CHAPTERS)} ${numbersOf(places)}`;
}

/** The same in the contents, a column with no room for the word: "also in 1", "also in 1, 4". */
export function alsoInShort(places: readonly number[]): string {
	return `${ALSO_IN} ${numbersOf(places)}`;
}

/**
 * The chapter something leads to, as the reader knows it: by its number.
 * The review refuses a story that leads to a chapter it does not have.
 */
export function chapterNamed(chapters: readonly ToldChapter[], id: string): string {
	return `${A_CHAPTER} ${chapterNumber(chapters.findIndex((chapter) => chapter.id === id))}`;
}

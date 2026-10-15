/**
 * How a story's parts are numbered, named and counted on the page, said one
 * way wherever they are said: in a chapter's heading, beside a step, in the
 * head of a piece, in what the overview says a decision leads to.
 */

import type { FollowedChapter, FollowedStep } from '$lib/types';
import { CHANGED_LINES, counted, type CountedWords, FILES, wordsFor } from '$lib/utils/words';

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
// What threads are called where a part of the story counts those hanging in it
const THREADS: CountedWords = { one: 'thread', many: 'threads' };
// What stands between the two counts of a chapter's head
const BETWEEN_COUNTS = ' · ';
// What stands between the numbers of several chapters
const BETWEEN_NUMBERS = ', ';
// How a file says that other chapters tell it too, before it names them
const ALSO_IN = 'also in';
// What is said of a part, or of some of the chapters, the reader has read through
const READ = 'read';
// What a step whose code a round changed after the story was told is said to be, to whoever cannot see it step back
const CHANGED_AFTER_TOLD = 'changed after it was told';
// What stands between a step's place among its chapter's steps and how many they are, and between chapters read and
// how many there are
const OUT_OF = 'of';
// What the tag beside a story's title says once a later round moved the code on, before that round
const CODE_MOVED_ON_IN_ROUND = 'the code moved on in round';
// What a chapter's warning says of the steps a round changed, between how many and which round
const IN_THIS_CHAPTER_CHANGED_IN_ROUND = `in this ${A_CHAPTER} changed in round`;
// What is said of the changed lines no step told, between how many there were and how many there are now, and after both
const NO_STEP_TOLD_WHEN_TOLD = 'no step told when the story was told';
const NOW = 'now';
// What a step whose code is no longer found says, before its file and after it
const ITS_CODE_IN = 'Its code in';
const IS_NO_LONGER_FOUND = 'is no longer found';

// What stands between how much a story left out when it was told and how much it leaves out now
const THEN_AND_NOW = ' → ';

/** What the tag beside a story's title says of the code under it while that is the code it was told of. */
export const CODE_CURRENT = 'current';

/** What heads the warning of a chapter whose code a round changed after the story was told. */
export const CHANGED_AFTER_TOLD_HEAD = 'Changed after it was told.';
/** What that warning says of the code under it, and of the reasons beside it. */
export const CODE_BELOW_IS_CURRENT = 'The code below is current; the reasons beside it may not be.';
/** And last, while the agent tells the story again. */
export const AGENT_UPDATING_REASONS = 'The agent is updating them.';

/** The lines a step tells: the first and the last, both among them. */
type StepLines = FollowedStep['lines'];

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

/** The same of a step whose code a round changed after it was told: "Step 1.2, changed after it was told". */
export function changedStepNamed(number: string): string {
	return `${stepNamed(number)}, ${CHANGED_AFTER_TOLD}`;
}

/** What that tag says once a later round moved the code on: "the code moved on in round 2". */
export function codeMovedOnIn(round: number): string {
	return `${CODE_MOVED_ON_IN_ROUND} ${round}`;
}

/**
 * How many changed lines no step told when the story was told, then how
 * many none tells now, as its contents say beside what it leaves out: "2 → 5".
 */
export function leftOutThenAndNow(then: number, now: number): string {
	return `${then}${THEN_AND_NOW}${now}`;
}

/**
 * The same, with what it stands beside, said to whoever cannot see the
 * arrow: "Not in the story, 2 changed lines no step told when the story was
 * told, 5 now".
 */
export function leftOutThenAndNowSaid(then: number, now: number): string {
	return `${NOT_IN_THE_STORY}, ${counted(then, CHANGED_LINES)} ${NO_STEP_TOLD_WHEN_TOLD}, ${now} ${NOW}`;
}

/** How many of a chapter's steps a round changed, and which round: "3 steps in this chapter changed in round 2." */
export function stepsChangedIn(steps: number, round: number): string {
	return `${counted(steps, STEPS)} ${IN_THIS_CHAPTER_CHANGED_IN_ROUND} ${round}.`;
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
	return `${STEPS.one} ${stepPlace + FIRST_NUMBER} ${OUT_OF} ${steps}`;
}

/** What a part is called in the contents once the reader has read it through: "Chapter 2: The end, read". */
export function calledOnceRead(called: string): string {
	return `${called}, ${READ}`;
}

/** What a part is called in the contents while threads hang in it: "Chapter 2: The end, 2 threads". */
export function calledWithThreads(called: string, threads: number): string {
	return `${called}, ${counted(threads, THREADS)}`;
}

/** How many chapters a story has: "5 chapters", "1 chapter". */
export function chaptersIn(chapters: number): string {
	return counted(chapters, CHAPTERS);
}

/**
 * How many chapters a story has, as the head of its contents says: "5
 * chapters", and once the reader has read any of them through, "1 of 5 read".
 */
export function chaptersCounted(chapters: number, read: number): string {
	return read === 0 ? chaptersIn(chapters) : `${read} ${OUT_OF} ${chapters} ${READ}`;
}

/**
 * How much a chapter tells, as its head says: "3 files · 4 steps"; "1 step" where none of its steps shows code
 * of any file any more.
 */
export function filesAndSteps(files: number, steps: number): string {
	if (files === 0) return counted(steps, STEPS);
	return [counted(files, FILES), counted(steps, STEPS)].join(BETWEEN_COUNTS);
}

/** What a step whose code the review cannot place in the change now says in its place. */
export function codeNoLongerFound(file: string): string {
	return `${ITS_CODE_IN} ${file} ${IS_NO_LONGER_FOUND}.`;
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
export function chapterNamed(chapters: readonly FollowedChapter[], id: string): string {
	return `${A_CHAPTER} ${chapterNumber(chapters.findIndex((chapter) => chapter.id === id))}`;
}

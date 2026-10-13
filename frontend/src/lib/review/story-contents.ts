/**
 * What a story lists of itself, read off its steps once for the story held.
 *
 * A story says its chapters and the steps of each. Which files a chapter
 * tells, and which other chapters tell a file of it, no field of it says:
 * both are read off the steps. Every head the story draws asks one or the
 * other, so they are worked out here once, not at each head.
 */

import { stepSectionKey } from '$lib/review/story-pieces';
import type { DiffFile, ToldChapter, ToldStep, ToldStory } from '$lib/types';

/**
 * What each part of a story is known by on the page: its overview, each
 * chapter, and what it leaves out. A chapter is known by its id, under a
 * word no other part begins with, so no id an agent chooses is another
 * part's key.
 */
export const OVERVIEW_PART = 'overview';
export const LEFT_OUT_PART = 'left-out';
const CHAPTER_PART = 'chapter';
// What stands between the two halves of a chapter's key
const KEY_SEPARATOR = ':';

/** A file as a chapter lists it: once, however many of the chapter's steps tell lines of it. */
interface FileListed {
	/** The file as the first of the chapter's pieces of it says: its path, and what became of it. */
	file: DiffFile;
	/** The other chapters that tell the file, by their places among the story's chapters, in the story's order. */
	alsoIn: number[];
}

/** A step as its chapter lists it. */
export interface StepListed {
	told: ToldStep;
	/** What the step's section of the page is known by. */
	section: string;
	/** Where the step stands among its chapter's steps: what it is numbered by, after its chapter. */
	place: number;
	/** The step's file, as its chapter lists it: one listing for every step of the file. */
	file: FileListed;
}

/** A chapter as the story lists it. */
export interface ChapterListed {
	told: ToldChapter;
	/** Where the chapter stands among the story's chapters: what it is numbered by. */
	place: number;
	/** What the chapter's part of the page is known by. */
	part: string;
	/** The files it tells, each once, in the order it first tells them. */
	files: FileListed[];
	/** Its steps, in the order it tells them. */
	steps: StepListed[];
}

/** What a story lists of itself: its chapters, in the order it tells them. */
export interface StoryContents {
	chapters: ChapterListed[];
}

/** Whether a chapter tells lines of a file. */
function tells(chapter: ToldChapter, path: string): boolean {
	return chapter.steps.some((step) => step.file === path);
}

/** The places of the chapters that tell a file, but for the one asked from, in the story's order. */
function otherChaptersTelling(path: string, askedFrom: number, chapters: readonly ToldChapter[]): number[] {
	return [...chapters.entries()]
		.filter(([place, chapter]) => place !== askedFrom && tells(chapter, path))
		.map(([place]) => place);
}

/**
 * A chapter as the story lists it. Its steps are walked once: a file is
 * listed at the first step that tells it, and every later step of the file
 * is given that same listing.
 */
function chapterListed(told: ToldChapter, place: number, chapters: readonly ToldChapter[]): ChapterListed {
	const files = new Map<string, FileListed>();
	const steps: StepListed[] = [];
	for (const [stepPlace, step] of told.steps.entries()) {
		const file = files.get(step.file) ?? {
			file: step.piece,
			alsoIn: otherChaptersTelling(step.file, place, chapters)
		};
		files.set(step.file, file);
		steps.push({ told: step, section: stepSectionKey(step), place: stepPlace, file });
	}
	const part = [CHAPTER_PART, told.id].join(KEY_SEPARATOR);
	return { told, place, part, files: [...files.values()], steps };
}

/** What a story lists of itself. */
export function contentsOf(story: ToldStory): StoryContents {
	return { chapters: story.chapters.map((told, place) => chapterListed(told, place, story.chapters)) };
}

/** What no story lists: while none is held, nothing is drawn. */
export const NO_CONTENTS: StoryContents = { chapters: [] };

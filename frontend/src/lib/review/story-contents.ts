/**
 * What a story lists of itself, read off its steps once for the story held.
 *
 * A story says its chapters and the steps of each. Which files a chapter
 * tells, which other chapters tell a file of it and how much the story
 * changes that file, no field of it says: all are read off its steps and
 * what it leaves out. Every head the story draws asks one or another, and
 * the contents beside it ask them all, so they are worked out here once.
 */

import { stepSectionKey } from '$lib/review/story-pieces';
import type { DiffFile, ToldChapter, ToldStep, ToldStory } from '$lib/types';
import { type FileStats, fileStats, totalOf } from '$lib/utils/file-stats';

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
	/** What the section of the chapter's first step of the file is known by: where a reader who picks the file is taken. */
	opensAt: string;
	/**
	 * How much the whole story changes the file: every piece it draws of it,
	 * a step's in any chapter or what no step tells. That is the file's whole
	 * change: the review refuses a line told twice, and what no step tells
	 * is drawn as left out. The diff on screen cannot be asked instead: it
	 * may be narrowed, or another take.
	 */
	change: FileStats;
	/** The other chapters that tell the file, by their places among the story's chapters, in the story's order. */
	alsoIn: number[];
	/** Whether no chapter before this one tells the file: the story first tells it here. */
	firstToldHere: boolean;
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

/**
 * What a story lists of itself: its chapters, in the order it tells them,
 * and each chapter and step by what its place on the page is known by. Both
 * are asked with what is being read, which may be nothing: nothing is then
 * found.
 */
export interface StoryContents {
	chapters: ChapterListed[];
	/** The chapter whose part is known by this key; null for the key of a part that is no chapter. */
	chapterAt: (part: string | null) => ChapterListed | null;
	/** The step whose section is known by this key, as its chapter lists it; null for a key no step has. */
	stepAt: (section: string | null) => StepListed | null;
}

/** What a table holds under a key: nothing under a key it does not hold, nor under none. */
function heldUnder<Held>(table: ReadonlyMap<string, Held>, key: string | null): Held | null {
	return key === null ? null : (table.get(key) ?? null);
}

/** Every piece of a file the story draws: each step's, then what no step tells. */
function piecesDrawn(story: ToldStory): DiffFile[] {
	const told = story.chapters.flatMap((chapter) => chapter.steps.map((step) => step.piece));
	return [...told, ...story.left_out.map((left) => left.piece)];
}

/** How much the whole story changes a file: every piece it draws of it, added up. */
function wholeChange(path: string, pieces: readonly DiffFile[]): FileStats {
	return totalOf(pieces.filter((piece) => piece.path === path).map(fileStats));
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
 * A file as a chapter lists it, from the first of the chapter's steps that tells it.
 *
 * @param first the first step of the chapter that tells the file
 * @param chapterPlace where that chapter stands among the story's
 * @param story the story, for the other chapters that tell the file
 * @param pieces every piece the story draws, for how much it changes the file
 */
function fileListed(first: ToldStep, chapterPlace: number, story: ToldStory, pieces: readonly DiffFile[]): FileListed {
	const alsoIn = otherChaptersTelling(first.file, chapterPlace, story.chapters);
	return {
		file: first.piece,
		opensAt: stepSectionKey(first),
		change: wholeChange(first.file, pieces),
		alsoIn,
		firstToldHere: alsoIn.every((other) => other > chapterPlace)
	};
}

/**
 * A chapter as the story lists it. Its steps are walked once: a file is
 * listed at the first step that tells it, and every later step of the file
 * is given that same listing.
 */
function chapterListed(told: ToldChapter, place: number, story: ToldStory, pieces: readonly DiffFile[]): ChapterListed {
	const files = new Map<string, FileListed>();
	const steps: StepListed[] = [];
	for (const [stepPlace, step] of told.steps.entries()) {
		const file = files.get(step.file) ?? fileListed(step, place, story, pieces);
		files.set(step.file, file);
		steps.push({ told: step, section: stepSectionKey(step), place: stepPlace, file });
	}
	const part = [CHAPTER_PART, told.id].join(KEY_SEPARATOR);
	return { told, place, part, files: [...files.values()], steps };
}

/** What a story lists of itself. */
export function contentsOf(story: ToldStory): StoryContents {
	const pieces = piecesDrawn(story);
	const chapters = story.chapters.map((told, place) => chapterListed(told, place, story, pieces));
	const byPart = new Map(chapters.map((chapter): [string, ChapterListed] => [chapter.part, chapter]));
	const bySection = new Map(
		chapters.flatMap((chapter) => chapter.steps).map((step): [string, StepListed] => [step.section, step])
	);
	return {
		chapters,
		chapterAt: (part) => heldUnder(byPart, part),
		stepAt: (section) => heldUnder(bySection, section)
	};
}

/** What no story lists: while none is held, nothing is drawn. */
export const NO_CONTENTS: StoryContents = { chapters: [], chapterAt: () => null, stepAt: () => null };

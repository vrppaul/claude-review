/**
 * What a story lists of itself, read off its steps once for the story held.
 *
 * A story says its chapters and the steps of each. Which files a chapter
 * tells, and which other chapters tell a file of it, no field of it says:
 * both are read off its steps. Every head the story draws asks one or
 * another, and the contents beside it ask them all, so they are worked out
 * here once.
 *
 * Here too every step, and whatever the story leaves out of a file, is
 * given what its section of the page is known by: this is the one walk of
 * the story that names them. The pieces the story draws are laid out from
 * this listing (`story-pieces.ts`), under the keys it gave.
 */

import { chapterPartKey, leftOutSectionKey, stepSectionKey } from '$lib/review/story-keys';
import type { DiffFile, LeftOut, ToldChapter, ToldStep, ToldStory } from '$lib/types';

/** A file as a chapter lists it: once, however many of the chapter's steps tell lines of it. */
export interface FileListed {
	/** The first of the chapter's pieces of the file, which says the file: its path, and what became of it. */
	firstPiece: DiffFile;
	/** What the section of the chapter's first step of the file is known by: where a reader who picks the file is taken. */
	opensAt: string;
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
	fileListed: FileListed;
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

/** What a story leaves out of a file, as the story lists it. */
export interface LeftOutListed {
	told: LeftOut;
	/** What its section of the page is known by. */
	section: string;
}

/**
 * What a story lists of itself: its chapters, in the order it tells them,
 * then what it leaves out, file by file; and each chapter and step by what
 * its place on the page is known by. Both are asked with what is being
 * read, which may be nothing: nothing is then found.
 */
export interface StoryContents {
	chapters: ChapterListed[];
	leftOut: LeftOutListed[];
	/** The chapter whose part is known by this key; null for the key of a part that is no chapter. */
	chapterAt: (part: string | null) => ChapterListed | null;
	/** The step whose section is known by this key, as its chapter lists it; null for a key no step has. */
	stepAt: (section: string | null) => StepListed | null;
}

/** That a chapter, by its place among the story's, tells lines of a file. */
interface ChapterTelling {
	path: string;
	place: number;
}

/** The chapters that tell each file, in the story's order: asked of every file a chapter lists. */
type ChaptersTelling = ReadonlyMap<string, readonly ChapterTelling[]>;

/** What a table holds under a key: nothing under a key it does not hold, nor under none. */
function heldUnder<Held>(table: ReadonlyMap<string, Held>, key: string | null): Held | null {
	return key === null ? null : (table.get(key) ?? null);
}

/** The files a chapter tells, each once. */
function filesTold(chapter: ToldChapter): Set<string> {
	return new Set(chapter.steps.map((step) => step.file));
}

/** Which chapters tell each file: the story's chapters walked once, for every file any of them lists. */
function chaptersTelling(chapters: readonly ToldChapter[]): ChaptersTelling {
	const tellings = chapters.flatMap((chapter, place) => [...filesTold(chapter)].map((path) => ({ path, place })));
	return Map.groupBy(tellings, ({ path }) => path);
}

/**
 * Whether a chapter is the first to tell a file it lists: no chapter before
 * it tells the file.
 */
export function tellsFirst(chapter: ChapterListed, listed: FileListed): boolean {
	return listed.alsoIn.every((other) => other > chapter.place);
}

/**
 * A file as a chapter lists it, from the first of the chapter's steps that tells it.
 *
 * @param first the first step of the chapter that tells the file
 * @param opensAt what that step's section is known by
 * @param chapterPlace where that chapter stands among the story's
 * @param telling which chapters tell each file
 */
function fileListed(first: ToldStep, opensAt: string, chapterPlace: number, telling: ChaptersTelling): FileListed {
	const tellers = telling.get(first.file) ?? [];
	return {
		firstPiece: first.piece,
		opensAt,
		alsoIn: tellers.map(({ place }) => place).filter((place) => place !== chapterPlace)
	};
}

/**
 * A chapter as the story lists it. Its steps are walked once: each is given
 * what its section is known by, a file is listed at the first step that
 * tells it, and every later step of the file is given that same listing.
 */
function chapterListed(told: ToldChapter, place: number, telling: ChaptersTelling): ChapterListed {
	const files = new Map<string, FileListed>();
	const steps: StepListed[] = [];
	for (const [stepPlace, step] of told.steps.entries()) {
		const section = stepSectionKey(step);
		const listed = files.get(step.file) ?? fileListed(step, section, place, telling);
		files.set(step.file, listed);
		steps.push({ told: step, section, place: stepPlace, fileListed: listed });
	}
	return { told, place, part: chapterPartKey(told), files: [...files.values()], steps };
}

/** What a story lists of itself. */
export function contentsOf(story: ToldStory): StoryContents {
	const telling = chaptersTelling(story.chapters);
	const chapters = story.chapters.map((told, place) => chapterListed(told, place, telling));
	const byPart = new Map(chapters.map((chapter): [string, ChapterListed] => [chapter.part, chapter]));
	const bySection = new Map(
		chapters.flatMap((chapter) => chapter.steps).map((step): [string, StepListed] => [step.section, step])
	);
	return {
		chapters,
		leftOut: story.left_out.map((told) => ({ told, section: leftOutSectionKey(told) })),
		chapterAt: (part) => heldUnder(byPart, part),
		stepAt: (section) => heldUnder(bySection, section)
	};
}

/** What no story lists: while none is held, nothing is drawn. */
export const NO_CONTENTS: StoryContents = { chapters: [], leftOut: [], chapterAt: () => null, stepAt: () => null };

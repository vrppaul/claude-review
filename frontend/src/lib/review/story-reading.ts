/**
 * The review read as the story the agent told of it: every step a section of
 * its own, in the order the story tells them, then what no step tells. The
 * threads on the story's own words are drawn here alone: under their blocks,
 * and at its head where the story held has no such block, which a story
 * told before it had — or where no story is held at all.
 *
 * A story draws a file in pieces — a step's lines, and whatever of the file
 * no step tells — so a file may stand in several sections, and a line of it
 * in at most one: the review refuses a story that tells a line twice. A
 * thread on a line no piece shows is not drawn here at all; read as Files,
 * against the review's own base, every thread is drawn.
 */

import { inDrawnOrder } from '$lib/anchors/placement';
import {
	askableReason,
	CHAPTER_TEXTS_IN_ORDER,
	chapterText,
	OVERVIEW_LINES_IN_ORDER,
	overviewItems,
	overviewLine,
	stepReason
} from '$lib/anchors/story';
import { tick } from 'svelte';
import type { ThreadLines } from '$lib/anchors/views';
import type { FileSections } from '$lib/dom/file-sections';
import type { ReadingPlace } from '$lib/dom/reading-place';
import type { ReadingParts } from '$lib/dom/reading-parts';
import {
	type Drawn,
	LINES_WITH_THEIR_THREADS,
	NOTHING_DRAWN,
	placeInLines,
	type PlaceRead,
	type ReadingView
} from '$lib/review/reading-view';
import type { ReviewStory } from '$lib/review/review-story.svelte';
import type { ChapterListed, FileListed } from '$lib/review/story-contents';
import { OVERVIEW_PART } from '$lib/review/story-keys';
import type { Threads } from '$lib/review/threads.svelte';
import type { LinePlace, StoryBlock, Thread, ToldStory } from '$lib/types';
import { namesTheFileAsItStands } from '$lib/utils/line-places';

// What the way back calls the parts of a story that are no chapter: its overview, and what no step tells
const OVERVIEW_CALLED = 'the overview';
const LEFT_OUT_CALLED = 'what no step tells';

/**
 * The threads on a block of the story's words, where the story says
 * something there: a text it left out, a doubt or a reason, is no block,
 * and draws none.
 */
function threadsOnWordsSaid(words: string | null, block: StoryBlock, threads: Threads): Thread[] {
	return words === null ? [] : threads.onBlock(block);
}

/** The threads on the overview's words, in the order it says them: on each line it says, then on each of its lists. */
export function threadsOnTheOverview(overview: ToldStory['overview'], threads: Threads): Thread[] {
	return [
		...OVERVIEW_LINES_IN_ORDER.flatMap((text) => threadsOnWordsSaid(overview[text], overviewLine(text), threads)),
		...overviewItems(overview).flatMap((block) => threads.onBlock(block))
	];
}

/**
 * The threads a chapter draws, in the order it says what they hang on: on
 * why its changes belong together, on where to doubt them, then step by
 * step on its reason and down the rows of its piece.
 */
export function threadsInTheChapter(chapter: ChapterListed, story: ReviewStory, threads: Threads): Thread[] {
	const { told } = chapter;
	return [
		...CHAPTER_TEXTS_IN_ORDER.flatMap((text) => threadsOnWordsSaid(told[text], chapterText(told.id, text), threads)),
		...chapter.steps.flatMap((step) => [
			...threadsOnWordsSaid(askableReason(step.told), stepReason(step.told.file, step.told.lines.first), threads),
			...threadsOnThePiece(step.section, step.told.file, story, threads)
		])
	];
}

/**
 * The threads on lines of a file that a chapter's pieces of it draw, down
 * their rows: those the contents count beside the file, under the chapter.
 */
export function threadsOnTheFileInTheChapter(
	chapter: ChapterListed,
	listed: FileListed,
	story: ReviewStory,
	threads: Threads
): Thread[] {
	return chapter.steps
		.filter((step) => step.shown?.fileListed === listed)
		.flatMap((step) => threadsOnThePiece(step.section, listed.firstPiece.path, story, threads));
}

/**
 * The threads on the story's words that no block of the story held draws,
 * in the order they were written: each on a block a story told before it
 * had, and it has not. They stand at the head of the story.
 */
export function threadsOffTheStory(story: ReviewStory, threads: Threads): Thread[] {
	return offTheStoryAmong(threadsPlaced(story, threads), threads);
}

/** The threads on the story's words that are none of those placed under what they hang on. */
function offTheStoryAmong(placed: readonly Thread[], threads: Threads): Thread[] {
	const drawnUnderTheirPlace = new Set(placed);
	return threads.onTheStory.flatMap(({ thread }) => (drawnUnderTheirPlace.has(thread) ? [] : [thread]));
}

/**
 * The threads the story held draws under what they hang on, part by part
 * down it: the overview's, each chapter's, then those on what no step
 * tells. None while no story is held.
 */
function threadsPlaced(story: ReviewStory, threads: Threads): Thread[] {
	const held = story.held;
	if (held === null) return [];
	return [
		...threadsOnTheOverview(held.story.overview, threads),
		...story.contents.chapters.flatMap((chapter) => threadsInTheChapter(chapter, story, threads)),
		...story.contents.leftOut.flatMap((left) => threadsOnThePiece(left.section, left.told.piece.path, story, threads))
	];
}

/**
 * The threads on lines of a file that the piece known by this section
 * draws, down its rows: none where that section draws no piece.
 */
export function threadsOnThePiece(section: string, path: string, story: ReviewStory, threads: Threads): Thread[] {
	return inDrawnOrder(threads.onLinesOf(path), (lines) => drawnBy(section, story.pieces.drawing(lines)));
}

/** A piece that draws a thread's lines, if it is the piece known by this key. */
function drawnBy<Piece extends { key: string }>(section: string, drawn: Piece | null): Piece | null {
	return drawn?.key === section ? drawn : null;
}

export class StoryReading implements ReadingView {
	readonly name = 'story';
	readonly readAs = 'story';
	readonly #story: ReviewStory;
	readonly #threads: Threads;
	// The sections its pieces are drawn in, and its parts: where the reader reads in it is in one or the other
	readonly #sections: FileSections;
	readonly #parts: ReadingParts;

	constructor(story: ReviewStory, threads: Threads, sections: FileSections, parts: ReadingParts) {
		this.#story = story;
		this.#threads = threads;
		this.#sections = sections;
		this.#parts = parts;
	}

	/**
	 * Until a story is told, no line: the threads on the words of a story
	 * told before, drawn at its head, and with none of those, nothing.
	 */
	drawn(): Drawn {
		if (this.#story.held === null) return { ...NOTHING_DRAWN, threads: this.threadsInOrder().length > 0 };
		return LINES_WITH_THEIR_THREADS;
	}

	sectionKeys(): string[] {
		return this.#story.pieces.keys;
	}

	/**
	 * Down the story, from its head: those on words it says nowhere, then
	 * part by part, the overview's, each chapter's, and those on what no step
	 * tells. Until a story is told, those at its head alone: on the words of
	 * a story told before.
	 */
	threadsInOrder(): Thread[] {
		const placed = threadsPlaced(this.#story, this.#threads);
		return [...offTheStoryAmong(placed, this.#threads), ...placed];
	}

	sectionOf(lines: ThreadLines): string | null {
		return this.#story.pieces.drawing(lines)?.key ?? null;
	}

	/** The first piece of the file the story draws: where the file is first told. */
	sectionOfFile(path: string): string | null {
		return this.#story.pieces.firstOf(path)?.key ?? null;
	}

	/** A line a piece draws: a piece reads nothing in around what it tells. */
	drawLine(path: string, line: LinePlace): Promise<string | null> {
		const drawing = this.#story.pieces.drawing({
			file: path,
			side: line.side,
			start_line: line.number,
			end_line: line.number
		});
		return Promise.resolve(drawing?.key ?? null);
	}

	/** A story folds nothing away. */
	unfold(): void {
		// Nothing of a story is folded: every piece it draws is on the page
	}

	/**
	 * In a piece of a file, called by its file and line; else in a part of
	 * the story, its overview or a chapter, called by its title.
	 */
	placeRead(): PlaceRead | null {
		const inAPiece = this.#sections.readingPlace(namesTheFileAsItStands);
		if (inAPiece !== null) return placeInLines(this.#sections, inAPiece);
		const inAPart = this.#parts.readingPlace(namesTheFileAsItStands);
		if (inAPart === null) return null;
		const called = this.#partCalled(inAPart.within);
		return { place: inAPart, called, calledInFull: called };
	}

	/** A story draws every piece and part it tells whole: once it is drawn, the place is there. */
	async returnTo(place: ReadingPlace): Promise<boolean> {
		await tick();
		if (this.#story.pieces.keys.includes(place.within)) this.#sections.goBackTo(place);
		else this.#parts.goBackTo(place);
		return true;
	}

	/** What a part of the story is called: a chapter by its title, the rest by what they are. */
	#partCalled(part: string): string {
		const chapter = this.#story.contents.chapterAt(part);
		if (chapter !== null) return chapter.told.title;
		return part === OVERVIEW_PART ? OVERVIEW_CALLED : LEFT_OUT_CALLED;
	}
}

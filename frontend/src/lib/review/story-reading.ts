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
 * thread on a line no piece shows is not drawn here at all; the files,
 * read against the review's own base, draw every thread.
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
import type { FileLines } from '$lib/anchors/views';
import { type Drawn, LINES_WITH_THEIR_THREADS, NOTHING_DRAWN, type ReadingView } from '$lib/review/reading-view';
import type { ReviewStory } from '$lib/review/review-story.svelte';
import type { ChapterListed, FileListed } from '$lib/review/story-contents';
import type { Threads } from '$lib/review/threads.svelte';
import type { StoryBlock, Thread, ToldStory } from '$lib/types';

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
	readonly #story: ReviewStory;
	readonly #threads: Threads;

	constructor(story: ReviewStory, threads: Threads) {
		this.#story = story;
		this.#threads = threads;
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

	sectionOf(lines: FileLines): string | null {
		return this.#story.pieces.drawing(lines)?.key ?? null;
	}

	/** The first piece of the file the story draws: where the file is first told. */
	sectionOfFile(path: string): string | null {
		return this.#story.pieces.firstOf(path)?.key ?? null;
	}

	/** A story folds nothing away. */
	unfold(): void {
		// Nothing of a story is folded: every piece it draws is on the page
	}
}

/**
 * The review read as the story the agent told of it: every step a section of
 * its own, in the order the story tells them, then what no step tells. The
 * threads on the story's own words are drawn here alone: under their blocks,
 * and at its head where the story held has no such block, which a story
 * told before it had.
 *
 * A story draws a file in pieces — a step's lines, and whatever of the file
 * no step tells — so a file may stand in several sections, and a line of it
 * in at most one: the review refuses a story that tells a line twice. A
 * thread on a line no piece shows is not drawn here at all; the files,
 * read against the review's own base, draw every thread. Nor is any thread
 * on lines drawn in a story told of another take of the change than the
 * page reads: its lines are numbered as that take, and a thread hangs on a
 * line of the take on screen.
 */

import type { StoryNumbering } from '$lib/anchors/numbering';
import { inDrawnOrder } from '$lib/anchors/placement';
import {
	askableReason,
	CHAPTER_TEXTS_IN_ORDER,
	chapterText,
	OVERVIEW_LINES_IN_ORDER,
	OVERVIEW_LISTS_IN_ORDER,
	overviewItem,
	overviewLine,
	stepReason
} from '$lib/anchors/story';
import type { FileLines } from '$lib/anchors/views';
import { type Drawn, LINES_WITH_THEIR_THREADS, NOTHING_DRAWN, type ReadingView } from '$lib/review/reading-view';
import type { ReviewStory } from '$lib/review/review-story.svelte';
import type { ChapterListed } from '$lib/review/story-contents';
import type { Threads } from '$lib/review/threads.svelte';
import type { DiffFile, StoryBlock, Thread, ToldStory } from '$lib/types';

/**
 * The threads on a block of the story's words, where the story says
 * something there: a text it left out, a doubt or a reason, is no block,
 * and draws none.
 */
function threadsOnWordsSaid(words: string | null, block: StoryBlock, threads: Threads): Thread[] {
	return words === null ? [] : threads.onBlock(block);
}

/** The threads on the overview's words, in the order it says them: its lines it says, then each of its lists. */
export function threadsOnTheOverview(overview: ToldStory['overview'], threads: Threads): Thread[] {
	const items = OVERVIEW_LISTS_IN_ORDER.flatMap((list) => overview[list].map((_, item) => overviewItem(list, item)));
	return [
		...OVERVIEW_LINES_IN_ORDER.flatMap((text) => threadsOnWordsSaid(overview[text], overviewLine(text), threads)),
		...items.flatMap((block) => threads.onBlock(block))
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
			...threadsOnThePiece(step.section, step.told.piece, story, threads)
		])
	];
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
		...story.contents.leftOut.flatMap((left) => threadsOnThePiece(left.section, left.told.piece, story, threads))
	];
}

/** The threads on lines one piece of a file draws, down its rows. */
function threadsOnThePiece(section: string, piece: DiffFile, story: ReviewStory, threads: Threads): Thread[] {
	return inDrawnOrder(threads.onLinesOf(piece.path), (lines) =>
		drawnBy(section, story.pieces.drawing(lines, story.numbering))
	);
}

/** A piece that draws a thread's lines, if it is the piece known by this key. */
function drawnBy<Piece extends { key: string }>(section: string, drawn: Piece | null): Piece | null {
	return drawn?.key === section ? drawn : null;
}

// What a story held draws, by whose numbers its lines carry: only the review's own take a comment, and
// only they carry threads
const DRAWN_NUMBERED: Record<StoryNumbering, Drawn> = {
	'the-reviews': LINES_WITH_THEIR_THREADS,
	'another-takes': { lines: 'to-read', threads: false }
};

export class StoryReading implements ReadingView {
	readonly name = 'story';
	readonly #story: ReviewStory;
	readonly #threads: Threads;

	constructor(story: ReviewStory, threads: Threads) {
		this.#story = story;
		this.#threads = threads;
	}

	/** Nothing until a story is told; and of a story told of another take, lines that are read and take nothing. */
	drawn(): Drawn {
		return this.#story.held === null ? NOTHING_DRAWN : DRAWN_NUMBERED[this.#story.numbering];
	}

	sectionKeys(): string[] {
		return this.#story.pieces.keys;
	}

	/**
	 * Down the story, from its head: those on words it says nowhere, then
	 * part by part, the overview's, each chapter's, and those on what no step
	 * tells. None until a story is told.
	 */
	threadsInOrder(): Thread[] {
		if (this.#story.held === null) return [];
		const placed = threadsPlaced(this.#story, this.#threads);
		return [...offTheStoryAmong(placed, this.#threads), ...placed];
	}

	sectionOf(lines: FileLines): string | null {
		return this.#story.pieces.drawing(lines, this.#story.numbering)?.key ?? null;
	}

	/**
	 * The first piece of the file the story draws: where the file is first
	 * told. None in a story of another take: its pieces are the file as it
	 * was, and whoever names a file means it as it is.
	 */
	sectionOfFile(path: string): string | null {
		if (this.#story.numbering === 'another-takes') return null;
		return this.#story.pieces.firstOf(path)?.key ?? null;
	}

	/** A story folds nothing away. */
	unfold(): void {
		// Nothing of a story is folded: every piece it draws is on the page
	}
}

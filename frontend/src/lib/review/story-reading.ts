/**
 * The review read as the story the agent told of it: every step a section of
 * its own, in the order the story tells them, then what no step tells. The
 * threads on the story's own words are drawn here alone, under their blocks.
 *
 * A story draws a file in pieces — a step's lines, and whatever of the file
 * no step tells — so a file may stand in several sections, and a line of it
 * in at most one: the review refuses a story that tells a line twice. A
 * thread on a line no piece shows is not drawn here at all; the files,
 * read against the review's own base, draw every thread. Nor is any thread
 * drawn in a story told of another take of the change than the page reads:
 * its lines are numbered as that take, and a thread hangs on a line of the
 * take on screen.
 */

import type { StoryNumbering } from '$lib/anchors/numbering';
import { inDrawnOrder } from '$lib/anchors/placement';
import { overviewLine } from '$lib/anchors/story';
import type { FileLines } from '$lib/anchors/views';
import { type Drawn, LINES_WITH_THEIR_THREADS, NOTHING_DRAWN, type ReadingView } from '$lib/review/reading-view';
import type { ReviewStory } from '$lib/review/review-story.svelte';
import type { Threads } from '$lib/review/threads.svelte';
import type { Thread } from '$lib/types';

// The overview's three lines, in the order the story says them
const OVERVIEW_LINES = (['task', 'done', 'doubt'] as const).map(overviewLine);

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

	/** Down the story: the threads on the overview's lines in the order it says them, then piece by piece and row by row, only those a piece draws. */
	threadsInOrder(): Thread[] {
		if (this.#story.held === null) return [];
		const pieces = this.#story.pieces;
		const numbering = this.#story.numbering;
		return [
			...OVERVIEW_LINES.flatMap((block) => this.#threads.onBlock(block)),
			...inDrawnOrder(this.#threads.onLines, (lines) => pieces.drawing(lines, numbering))
		];
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

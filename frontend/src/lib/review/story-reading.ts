/**
 * The review read as the story the agent told of it: every step a section of
 * its own, in the order the story tells them, then what no step tells.
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

import { inDrawnOrder } from '$lib/anchors/placement';
import type { FileLines } from '$lib/anchors/views';
import type { ReadingView } from '$lib/review/reading-view';
import type { ReviewStory } from '$lib/review/review-story.svelte';
import type { Threads } from '$lib/review/threads.svelte';
import type { Thread } from '$lib/types';

export class StoryReading implements ReadingView {
	readonly name = 'story';
	readonly #story: ReviewStory;
	readonly #threads: Threads;

	constructor(story: ReviewStory, threads: Threads) {
		this.#story = story;
		this.#threads = threads;
	}

	sectionKeys(): string[] {
		return this.#story.pieces.keys;
	}

	/** Down the story, piece by piece and row by row: only the threads a piece draws. */
	threadsInOrder(): Thread[] {
		const pieces = this.#story.pieces;
		const numbering = this.#story.numbering;
		return inDrawnOrder(this.#threads.onLines, (lines) => pieces.drawing(lines, numbering));
	}

	sectionOf(lines: FileLines): string | null {
		return this.#story.pieces.drawing(lines, this.#story.numbering)?.key ?? null;
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

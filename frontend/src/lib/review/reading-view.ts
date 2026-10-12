/**
 * A way the review is read on screen: which sections it draws, in what
 * order, and which of them draws a given line or file.
 *
 * Threads, keys and whatever takes the reader somewhere are the same however
 * the review is read; what differs is what is on the page. Each way of
 * reading answers for that here, so moving the reader never asks which one
 * is on screen — and another way of reading the same change is another
 * answer to these questions, not a branch in whoever asks them.
 */

import { inDiffOrder, isDrawn } from '$lib/anchors/placement';
import type { FileLines } from '$lib/anchors/views';
import type { ReadingViewName } from '$lib/reader/page-layout.svelte';
import type { ReadingProgress } from '$lib/review/reading-progress.svelte';
import type { ReviewDiff } from '$lib/review/review-diff.svelte';
import type { Threads } from '$lib/review/threads.svelte';
import type { Thread } from '$lib/types';

export interface ReadingView {
	/** Which way of reading it is: what the reader chooses it by, and what is its alone is known by. */
	readonly name: ReadingViewName;
	/** The sections it draws, by their keys, in the order it draws them: what ] and [ walk. */
	sectionKeys: () => string[];
	/** The threads it draws, in the order they stand in it: what n and p walk. */
	threadsInOrder: () => Thread[];
	/** The section a thread on these lines is drawn in, by its key; null where the view draws no such thread. */
	sectionOf: (lines: FileLines) => string | null;
	/** The section the reader is taken to for a file, by its key; null where the view draws none of the file. */
	sectionOfFile: (path: string) => string | null;
	/** Bring out lines the view has folded away, so what hangs on them can be drawn. */
	unfold: (lines: FileLines) => void;
}

/**
 * The threads on lines that a view draws none of. They are still in the
 * review and still go out with the round: whoever shows the view counts
 * them and offers the way to where they are drawn.
 */
export function threadsNotDrawnIn(view: ReadingView, threads: Threads): Thread[] {
	return threads.onLines.filter(({ lines }) => view.sectionOf(lines) === null).map(({ thread }) => thread);
}

/** What the files' own view knows a file's section by: its path, since it draws each file once. */
export function fileSectionKey(path: string): string {
	return path;
}

/** The review read file by file: every file of the diff on screen in a section of its own, in the diff's order. */
export class FilesReading implements ReadingView {
	readonly name = 'files';
	readonly #diff: ReviewDiff;
	readonly #threads: Threads;
	readonly #reading: ReadingProgress;

	constructor(diff: ReviewDiff, threads: Threads, reading: ReadingProgress) {
		this.#diff = diff;
		this.#threads = threads;
		this.#reading = reading;
	}

	sectionKeys(): string[] {
		return this.#diff.files.map((file) => fileSectionKey(file.path));
	}

	/**
	 * Down the diff, file by file and row by row; those on files it no longer
	 * holds first, as they are drawn above it. Under a narrower base, only
	 * the threads that base draws.
	 */
	threadsInOrder(): Thread[] {
		const drawn = this.#threads.onLines.filter(({ lines }) => this.sectionOf(lines) !== null);
		return inDiffOrder(drawn, this.#diff.files);
	}

	/**
	 * Read against the review's own base, every thread is drawn somewhere
	 * here: under its line, at the head of its file where the line is not
	 * shown, or above the files where the diff no longer holds the file.
	 * Each is found from the file's section. A narrower base draws only the
	 * threads on lines it shows whose numbers are the review's own; the rest
	 * are drawn once the whole review is put back.
	 */
	sectionOf(lines: FileLines): string | null {
		const leftOut = this.#diff.narrowed && !isDrawn(lines, this.#diff.files, this.#diff.numbering);
		return leftOut ? null : fileSectionKey(lines.file);
	}

	sectionOfFile(path: string): string | null {
		return this.#diff.files.some((file) => file.path === path) ? fileSectionKey(path) : null;
	}

	/** A folded file draws no line, and no thread: it is opened. */
	unfold(lines: FileLines): void {
		this.#reading.unfold(lines.file);
	}
}

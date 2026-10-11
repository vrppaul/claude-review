/**
 * Moving the reader through the review: from thread to thread, whatever
 * each hangs on, and from file to file.
 *
 * Naming a thread is the anchor's business and touches nothing; bringing one
 * into view opens what hides it and moves the screen, so it lives here, with
 * the parts of the page it moves — and so does where the reader has got to
 * among the threads, which only moving changes. Every control that moves the
 * reader — the keys, the header's arrows, the replies — moves them through here.
 */

import type { FileSections } from '$lib/dom/file-sections';
import type { ReadingProgress } from '$lib/review/reading-progress.svelte';
import type { ReviewDiff } from '$lib/review/review-diff.svelte';
import type { Threads } from '$lib/review/threads.svelte';
import type { Thread, LineAnchor } from '$lib/types';

/**
 * Where a step lands among this many threads, from the one at `here`: the
 * next or the previous, round from the end to the start. From nowhere — no
 * thread yet, or the one the reader was on is gone — going on starts at the
 * first and going back at the last.
 */
function steppedTo(here: number, direction: 1 | -1, count: number): number {
	if (here === -1) return direction === 1 ? 0 : count - 1;
	return (here + direction + count) % count;
}

export class Navigator {
	readonly #threads: Threads;
	readonly #reading: ReadingProgress;
	readonly #sections: FileSections;
	readonly #diff: ReviewDiff;
	// The thread the reader was last brought to, by whichever control, and the
	// one a step goes on from. Kept by id: threads come and go, and a place in
	// the list would then be another thread's.
	#atThread: string | null = null;

	constructor(threads: Threads, reading: ReadingProgress, sections: FileSections, diff: ReviewDiff) {
		this.#threads = threads;
		this.#reading = reading;
		this.#sections = sections;
		this.#diff = diff;
	}

	/** Step to the next or previous thread, and bring it into view. */
	step(direction: 1 | -1): void {
		const threads = this.#threads.all;
		const here = threads.findIndex((thread) => thread.id === this.#atThread);
		const next = threads[steppedTo(here, direction, threads.length)];
		if (next) this.reveal(next);
	}

	/** Bring a thread into view, and go on from it the next time the reader steps. */
	reveal(thread: Thread): void {
		this.#atThread = thread.id;
		const { anchor } = thread;
		switch (anchor.kind) {
			case 'line':
				this.#revealOnLines(thread.id, anchor);
				return;
			default:
				return unknownKind(anchor.kind);
		}
	}

	/** Bring a thread into view to read its answer, which reading it marks read. */
	readAnswer(thread: Thread): void {
		this.reveal(thread);
		this.#threads.reading.markRead(thread.id);
	}

	/** Go to the oldest thread carrying an answer nobody has looked at, if any does. */
	nextUnread(): void {
		const [oldest] = this.#threads.unread;
		if (oldest) this.readAnswer(oldest);
	}

	/**
	 * Step to the next or previous file from the one the reader is in — by
	 * focus if a line in it has the focus, by scroll if not — and bring it into
	 * view; from nowhere, the first or the last.
	 */
	stepFile(direction: 1 | -1): void {
		const files = this.#diff.files;
		if (files.length === 0) return;
		const here = this.#sections.current();
		const from = files.findIndex((file) => file.path === here);
		const first = direction === 1 ? 0 : files.length - 1;
		const to = from === -1 ? first : Math.min(files.length - 1, Math.max(0, from + direction));
		this.#sections.scrollToFile(files[to].path);
	}

	#revealOnLines(threadId: string, anchor: LineAnchor): void {
		// A folded file has no thread on screen to move to, so it is opened
		// first; the thread is brought into view once it is drawn
		this.#reading.unfold(anchor.file);
		this.#sections.scrollToThread(threadId, anchor.file);
	}
}

/** The compiler's way of saying a kind of anchor was left out above. */
function unknownKind(kind: never): never {
	throw new Error(`No way to bring a thread on ${String(kind)} into view`);
}

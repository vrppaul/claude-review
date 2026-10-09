/**
 * Moving the reader from thread to thread, whatever each hangs on.
 *
 * Naming a thread is the anchor's business and touches nothing; bringing one
 * into view opens what hides it and moves the screen, so it lives here, with
 * the parts of the page it moves — and so does where the reader has got to
 * among the threads, which only moving changes.
 */

import type { FileSections } from '$lib/dom/file-sections';
import type { ReadingProgress } from '$lib/review/reading-progress.svelte';
import type { Threads } from '$lib/review/threads.svelte';
import type { Thread, LineAnchor } from '$lib/types';

export class ThreadNavigator {
	readonly #threads: Threads;
	readonly #reading: ReadingProgress;
	readonly #sections: FileSections;
	// Where the reader is among the threads, shared by every control that steps through them
	#position = -1;

	constructor(threads: Threads, reading: ReadingProgress, sections: FileSections) {
		this.#threads = threads;
		this.#reading = reading;
		this.#sections = sections;
	}

	/** Step to the next or previous thread, and bring it into view. */
	step(direction: 1 | -1): void {
		const threads = this.#threads.all;
		if (threads.length === 0) return;
		this.#position = (this.#position + direction + threads.length) % threads.length;
		this.reveal(threads[this.#position]);
	}

	reveal(thread: Thread): void {
		const { anchor } = thread;
		switch (anchor.kind) {
			case 'line':
				this.#revealOnLines(thread.id, anchor);
				return;
			default:
				return unknownKind(anchor.kind);
		}
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

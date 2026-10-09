/**
 * Bringing a thread into view, whatever it hangs on.
 *
 * Naming a thread is the anchor's business and touches nothing; bringing one
 * into view opens what hides it and moves the screen, so it lives here, with
 * the parts of the page it moves.
 */

import type { FileSections } from '$lib/review/file-sections';
import type { ReadingProgress } from '$lib/review/reading-progress.svelte';
import type { Thread, LineAnchor } from '$lib/types';

export class ThreadNavigator {
	readonly #reading: ReadingProgress;
	readonly #sections: FileSections;

	constructor(reading: ReadingProgress, sections: FileSections) {
		this.#reading = reading;
		this.#sections = sections;
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
		// A folded file has no thread on screen to move to, so it is opened first
		this.#reading.unfold(anchor.file);
		requestAnimationFrame(() => this.#sections.scrollToThread(threadId, anchor.file));
	}
}

/** The compiler's way of saying a kind of anchor was left out above. */
function unknownKind(kind: never): never {
	throw new Error(`No way to bring a thread on ${String(kind)} into view`);
}

import type { LinePlace, Thread } from '$lib/types';
import { type Numbering, sideIsTheReviews } from '$lib/anchors/numbering';
import type { ThreadOnLines } from '$lib/anchors/views';
import { placeKey } from '$lib/utils/line-places';

/** What a line with no threads under it holds. */
const NO_THREADS: readonly Thread[] = [];

/**
 * A file's threads by the line they hang under: the last line of what each
 * is about, on its side.
 *
 * Asking line by line turned one thread into a scan of the whole list per
 * line, which a long file pays for on every keystroke that changes it.
 */
export class ThreadsByLine {
	readonly #byLine = new Map<string, Thread[]>();

	/**
	 * @param threads the threads on lines of the file
	 * @param numbering whose numbers the lines drawn carry: a thread hangs only on a side whose numbers
	 *   are the review's own
	 */
	constructor(threads: readonly ThreadOnLines[], numbering: Numbering) {
		for (const { thread, lines } of threads) {
			if (!sideIsTheReviews(lines.side, numbering)) continue;
			const key = placeKey({ side: lines.side, number: lines.end_line });
			const existing = this.#byLine.get(key);
			if (existing) existing.push(thread);
			else this.#byLine.set(key, [thread]);
		}
	}

	/** The threads hanging under a line, in the order they were written. */
	at(place: LinePlace): readonly Thread[] {
		return this.#byLine.get(placeKey(place)) ?? NO_THREADS;
	}
}

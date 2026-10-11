import type { LinePlace, Thread } from '$lib/types';
import type { ThreadOnLines } from '$lib/anchors/line';
import { sideIsDrawn } from '$lib/anchors/placement';
import { placeKey } from '$lib/utils/drawn-file';

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
	 * @param removedLines whether threads on removed lines are drawn — see `isDrawn`: under a narrower
	 *   base those numbers belong to something else
	 */
	constructor(threads: readonly ThreadOnLines[], removedLines: boolean) {
		for (const { thread, lines } of threads) {
			if (!sideIsDrawn(lines.side, removedLines)) continue;
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

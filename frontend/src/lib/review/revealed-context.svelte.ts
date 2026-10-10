/**
 * Lines the reader revealed above hunks, for the one diff they were revealed in.
 *
 * A new diff — a round, a base, whitespace — renumbers the file, so each
 * diff gets a context of its own and the last one's goes with it. A reveal
 * still on its way when the diff is replaced lands in the context it was
 * asked in, which nothing draws any more.
 */

import { SvelteMap, SvelteSet } from 'svelte/reactivity';

import { readFileWindow } from '$lib/api/review-api';
import type { DiffLine } from '$lib/types';
import { type ContextGap, toContextLines } from '$lib/utils/expansions';

/** What a file with nothing revealed has above its hunks: nothing. */
const NOTHING_REVEALED: ReadonlyMap<string, DiffLine[]> = new Map();

/** What a read of a gap is known by while it is on its way: the file, and the hunk below the gap. */
function readingKey(path: string, hunk: string): string {
	return JSON.stringify([path, hunk]);
}

export class RevealedContext {
	// By file path, then by the hunk the lines sit above
	readonly #revealed = new SvelteMap<string, SvelteMap<string, DiffLine[]>>();
	// The gaps being read: kept here rather than by whatever draws a gap, which
	// may be drawn again while its read is out and would ask for the same
	// lines a second time
	readonly #reading = new SvelteSet<string>();

	/** Lines revealed for one file, by the hunk below them. */
	forFile(path: string): ReadonlyMap<string, DiffLine[]> {
		return this.#revealed.get(path) ?? NOTHING_REVEALED;
	}

	/** Whether the lines of a gap are on their way. */
	isReading(path: string, gap: ContextGap): boolean {
		return this.#reading.has(readingKey(path, gap.hunk));
	}

	/**
	 * Read the next lines of a gap and keep them above the hunk below it —
	 * unless they are already on their way: one read of a gap at a time.
	 *
	 * They go before the ones already there: a gap is always widened upward
	 * from the hunk below it.
	 */
	async reveal(path: string, gap: ContextGap): Promise<void> {
		const key = readingKey(path, gap.hunk);
		if (gap.next === null || this.#reading.has(key)) return;
		this.#reading.add(key);
		try {
			const read = await readFileWindow(path, gap.next.start, gap.next.end);
			const forPath = this.#revealed.get(path) ?? new SvelteMap<string, DiffLine[]>();
			const existing = forPath.get(gap.hunk) ?? [];
			forPath.set(gap.hunk, [...toContextLines(read.start, read.lines, gap.oldOffset), ...existing]);
			this.#revealed.set(path, forPath);
		} finally {
			this.#reading.delete(key);
		}
	}
}

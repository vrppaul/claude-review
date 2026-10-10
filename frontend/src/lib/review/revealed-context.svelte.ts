/**
 * Lines the reader revealed above hunks, for the one diff they were revealed in.
 *
 * A new diff — a round, a base, whitespace — renumbers the file, so each
 * diff gets a context of its own and the last one's goes with it. A reveal
 * still on its way when the diff is replaced lands in the context it was
 * asked in, which nothing draws any more.
 */

import { SvelteMap } from 'svelte/reactivity';

import { readFileWindow } from '$lib/api/review-api';
import type { DiffLine } from '$lib/types';
import { type ContextGap, toContextLines } from '$lib/utils/expansions';

/** What a file with nothing revealed has above its hunks: nothing. */
const NOTHING_REVEALED: ReadonlyMap<string, DiffLine[]> = new Map();

export class RevealedContext {
	// By file path, then by the hunk the lines sit above
	readonly #revealed = new SvelteMap<string, SvelteMap<string, DiffLine[]>>();

	/** Lines revealed for one file, by the hunk below them. */
	forFile(path: string): ReadonlyMap<string, DiffLine[]> {
		return this.#revealed.get(path) ?? NOTHING_REVEALED;
	}

	/**
	 * Read the next lines of a gap and keep them above the hunk below it.
	 *
	 * They go before the ones already there: a gap is always widened upward
	 * from the hunk below it.
	 */
	async reveal(path: string, gap: ContextGap): Promise<void> {
		if (gap.next === null) return;
		const read = await readFileWindow(path, gap.next.start, gap.next.end);
		const forPath = this.#revealed.get(path) ?? new SvelteMap<string, DiffLine[]>();
		const existing = forPath.get(gap.hunk) ?? [];
		forPath.set(gap.hunk, [...toContextLines(read.start, read.lines, gap.oldOffset), ...existing]);
		this.#revealed.set(path, forPath);
	}
}

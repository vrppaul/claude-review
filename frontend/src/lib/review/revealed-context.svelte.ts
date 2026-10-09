/**
 * Lines the reader revealed above hunks, for the diff they were revealed in.
 *
 * Revealed lines sit above hunks counted by position, and a new diff counts
 * them afresh — a round, a base, whitespace all renumber them — so they are
 * dropped with every new diff.
 */

import { SvelteMap } from 'svelte/reactivity';

import { readFileWindow } from '$lib/api/review-api';
import type { DiffLine } from '$lib/types';
import { toContextLines } from '$lib/utils/expansions';

/** What a file with nothing revealed has above its hunks: nothing. */
const NOTHING_REVEALED: ReadonlyMap<number, DiffLine[]> = new Map();

export class RevealedContext {
	// By file path, then by the index of the hunk the lines sit above
	readonly #revealed = new SvelteMap<string, SvelteMap<number, DiffLine[]>>();

	/** Lines revealed for one file, keyed by the index of the hunk below them. */
	forFile(path: string): ReadonlyMap<number, DiffLine[]> {
		return this.#revealed.get(path) ?? NOTHING_REVEALED;
	}

	revealedCount(path: string, hunkIndex: number): number {
		return this.#revealed.get(path)?.get(hunkIndex)?.length ?? 0;
	}

	/**
	 * Fetch a window of the file and keep it above the given hunk.
	 *
	 * Newly fetched lines go before the ones already there, since a gap is
	 * always widened upward from the hunk below it.
	 */
	async reveal(path: string, hunkIndex: number, start: number, end: number, oldOffset: number): Promise<void> {
		const read = await readFileWindow(path, start, end);
		const forPath = this.#revealed.get(path) ?? new SvelteMap();
		const existing = forPath.get(hunkIndex) ?? [];
		forPath.set(hunkIndex, [...toContextLines(read.start, read.lines, oldOffset), ...existing]);
		this.#revealed.set(path, forPath);
	}

	/** Drop everything revealed: a new diff counts its hunks afresh. */
	forget(): void {
		this.#revealed.clear();
	}
}

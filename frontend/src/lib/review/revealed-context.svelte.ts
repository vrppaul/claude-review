/**
 * Lines the reader revealed around hunks, for the one diff they were revealed in.
 *
 * A new diff — a round, a base, whitespace — renumbers the file, so each
 * diff gets a context of its own and the last one's goes with it. A reveal
 * still on its way when the diff is replaced lands in the context it was
 * asked in, which nothing draws any more.
 */

import { SvelteMap, SvelteSet } from 'svelte/reactivity';

import { readFileWindow } from '$lib/api/review-api';
import type { DiffLine } from '$lib/types';
import { type ContextGap, type GapRead, type RevealedLines, toContextLines } from '$lib/utils/expansions';

/** What a file with nothing revealed beside a hunk has there: nothing. */
const NOTHING_BESIDE: ReadonlyMap<string, DiffLine[]> = new Map();

/** Lines kept beside hunks: by file path, then by the hunk they are drawn beside. */
type Beside = SvelteMap<string, SvelteMap<string, DiffLine[]>>;

/** Keep what a file has beside one hunk, put together from what it had there. */
function keep(beside: Beside, path: string, hunk: string, withRead: (kept: DiffLine[]) => DiffLine[]): void {
	const forPath = beside.get(path) ?? new SvelteMap<string, DiffLine[]>();
	forPath.set(hunk, withRead(forPath.get(hunk) ?? []));
	beside.set(path, forPath);
}

/** What a read of a gap is known by while it is on its way: the file, and the gap. */
function readingKey(path: string, gap: string): string {
	return JSON.stringify([path, gap]);
}

export class RevealedContext {
	// The lines drawn above hunks, and those drawn below them
	readonly #above: Beside = new SvelteMap();
	readonly #below: Beside = new SvelteMap();
	// How long each file is, as the last read of it said
	readonly #lengths = new SvelteMap<string, number>();
	// The gaps being read: kept here rather than by whatever draws a gap, which
	// may be drawn again while its read is out and would ask for the same
	// lines a second time
	readonly #reading = new SvelteSet<string>();

	/** Lines revealed beside one file's hunks, and how long the file is once a read has said. */
	forFile(path: string): RevealedLines {
		return {
			above: this.#above.get(path) ?? NOTHING_BESIDE,
			below: this.#below.get(path) ?? NOTHING_BESIDE,
			length: this.#lengths.get(path) ?? null
		};
	}

	/** Whether the lines of a gap are on their way. */
	isReading(path: string, gap: ContextGap): boolean {
		return this.#reading.has(readingKey(path, gap.key));
	}

	/**
	 * Read lines into a gap and keep them beside the hunk they were read from —
	 * unless lines of that gap are already on their way: one read of a gap at
	 * a time. Every read says how long the file is, which the gap below the
	 * last hunk is measured by.
	 */
	async reveal(path: string, read: GapRead): Promise<void> {
		const key = readingKey(path, read.gap);
		if (this.#reading.has(key)) return;
		this.#reading.add(key);
		try {
			const answer = await readFileWindow(path, read.window.start, read.window.end);
			this.#lengths.set(path, answer.total);
			const lines = toContextLines(answer.start, answer.lines, read.oldOffset);
			const { hunk, side } = read.landing;
			// Above a hunk the lines read go before those already there: a gap is
			// widened up from the hunk below it; below one, after them
			if (side === 'above') keep(this.#above, path, hunk, (kept) => [...lines, ...kept]);
			else keep(this.#below, path, hunk, (kept) => [...kept, ...lines]);
		} finally {
			this.#reading.delete(key);
		}
	}
}

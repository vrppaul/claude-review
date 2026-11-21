/**
 * The code round the places of a name, read for the window that shows it
 * beside them. A place may stand in any file of the take, the change's or
 * one it left, so each is read from the take as the review wrote it down,
 * its lines numbered as the places are. A file is read whole, once while
 * the window is open, and highlighted as a document: a comment opened above
 * the lines shown is coloured as one.
 */

import { SvelteMap } from 'svelte/reactivity';
import { readFileOfTake } from '$lib/api/review-api';
import type { ReviewMode } from '$lib/types';
import { NO_NUMBER } from '$lib/utils/drawn-file';
import { messageOf } from '$lib/utils/errors';
import { type HighlightedLine, highlightHunk, languageOf } from '$lib/utils/highlight';

/** What reading a file came to: on its way, its lines highlighted, or why it could not be read. */
export type CodeRead =
	{ kind: 'reading' } | { kind: 'read'; lines: readonly HighlightedLine[] } | { kind: 'failed'; why: string };

// A read on its way
const READING: CodeRead = { kind: 'reading' };

// How many lines of its file are shown either side of a place, as the board draws them: a method round a call or a
// definition's head and body, all of which stand whole in the window at its full height; in a shorter window the
// column scrolls to the rest
const LINES_ROUND_A_PLACE = 9;

/** Read a file of the take on screen whole, highlighted as what its kind of review reads it as, and say what came of it. */
async function readHighlighted(path: string, mode: ReviewMode): Promise<CodeRead> {
	try {
		const file = await readFileOfTake(path);
		return { kind: 'read', lines: highlightHunk(file.hunk.lines, languageOf(mode, path)) };
	} catch (error) {
		return { kind: 'failed', why: messageOf(error) };
	}
}

/** A file's lines round one of them: as many either side as are shown, fewer where the file starts or ends. */
export function linesRound(lines: readonly HighlightedLine[], line: number): HighlightedLine[] {
	return lines.filter((drawn) => Math.abs((drawn.line.new_number ?? NO_NUMBER) - line) <= LINES_ROUND_A_PLACE);
}

export class PlacesCode {
	readonly #mode: ReviewMode;
	// What reading each file asked for came to, by its path
	readonly #reads = new SvelteMap<string, CodeRead>();

	/** @param mode the kind of review, which says what a file is highlighted as */
	constructor(mode: ReviewMode) {
		this.#mode = mode;
	}

	/** What reading a file came to; on its way until it is asked for. */
	of(path: string): CodeRead {
		return this.#reads.get(path) ?? READING;
	}

	/** Read a file, unless it is read or on its way: again where its read failed. */
	read(path: string): void {
		const held = this.#reads.get(path);
		if (held === undefined || held.kind === 'failed') void this.#read(path);
	}

	/** Read a file, holding that it is on its way until its read comes. */
	async #read(path: string): Promise<void> {
		this.#reads.set(path, READING);
		this.#reads.set(path, await readHighlighted(path, this.#mode));
	}
}

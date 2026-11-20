/**
 * The way back to where the reader was before the page took them to a line.
 *
 * A reader taken somewhere they did not scroll to has left their own place:
 * the places they leave stack up, and Back takes them to the last. A place
 * is of the diff it was read in: another diff — a retake, another base —
 * numbers the lines anew, so the places left in the one before lead nowhere
 * true, and none is offered.
 */

import type { ReadingViewName } from '$lib/reader/page-layout.svelte';
import type { ReviewDiff } from '$lib/review/review-diff.svelte';
import type { DiffFile, LinePlace } from '$lib/types';

/** Where the reader was as the page took them elsewhere. */
export interface PlaceLeft {
	/** The view they read the review in. */
	view: ReadingViewName;
	/** The section they read in, by the key its view knows it by. */
	section: string;
	/** The file it draws lines of. */
	path: string;
	/** The line they read from; null for the section's top. */
	line: LinePlace | null;
}

/** The places left, and the diff they were read in, by its files. */
interface Stack {
	readIn: readonly DiffFile[];
	places: readonly PlaceLeft[];
}

export class WayBack {
	readonly #diff: ReviewDiff;
	#stack: Stack;

	/** @param diff the diff on screen, whose places a stack holds */
	constructor(diff: ReviewDiff) {
		this.#diff = diff;
		this.#stack = $state.raw({ readIn: diff.files, places: [] });
	}

	/** The place Back takes the reader to: the last they left in the diff on screen; null where they left none. */
	get top(): PlaceLeft | null {
		const { readIn, places } = this.#stack;
		return readIn === this.#diff.files ? (places.at(-1) ?? null) : null;
	}

	/** The reader leaves a place, read in the diff on screen: on top of those they left in it before. */
	note(place: PlaceLeft): void {
		const readIn = this.#diff.files;
		const before = this.#stack.readIn === readIn ? this.#stack.places : [];
		this.#stack = { readIn, places: [...before, place] };
	}

	/** Take the place Back goes to off the stack, and hand it over; null where there is none. */
	takeTop(): PlaceLeft | null {
		const top = this.top;
		if (top !== null) this.#stack = { ...this.#stack, places: this.#stack.places.slice(0, -1) };
		return top;
	}
}

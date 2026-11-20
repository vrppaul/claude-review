/**
 * The way back to where the reader was before the page took them to a line.
 *
 * A reader taken somewhere they did not scroll to has left their own place:
 * the places they leave stack up, and Back takes them to the last. A place
 * is of the take it was read in: another take of the diff numbers the lines
 * anew, so the places left in the one before lead nowhere true, and none is
 * offered. Another base over the same take numbers the file as it stands
 * the same, and keeps them.
 */

import type { PlaceRead, ReadingViewName } from '$lib/review/reading-view';
import type { ReviewDiff } from '$lib/review/review-diff.svelte';

/** Where the reader was as the page took them elsewhere: the view they read in, and where in it. */
export interface PlaceLeft extends PlaceRead {
	view: ReadingViewName;
}

/** The places left, and the take of the diff they were read in. */
interface Stack {
	take: number;
	places: readonly PlaceLeft[];
}

export class WayBack {
	readonly #diff: ReviewDiff;
	#stack: Stack;

	/** @param diff the diff on screen, whose take a stack is of */
	constructor(diff: ReviewDiff) {
		this.#diff = diff;
		this.#stack = $state.raw({ take: diff.takeOnScreen, places: [] });
	}

	/** The place Back takes the reader to: the last they left in the take on screen; null where they left none. */
	get top(): PlaceLeft | null {
		const { take, places } = this.#stack;
		return take === this.#diff.takeOnScreen ? (places.at(-1) ?? null) : null;
	}

	/** The reader leaves a place, read in the take on screen: on top of those they left in it before. */
	note(place: PlaceLeft): void {
		const take = this.#diff.takeOnScreen;
		const before = this.#stack.take === take ? this.#stack.places : [];
		this.#stack = { take, places: [...before, place] };
	}

	/** Take the place Back goes to off the stack, and hand it over; null where there is none. */
	takeTop(): PlaceLeft | null {
		const top = this.top;
		if (top !== null) this.#stack = { ...this.#stack, places: this.#stack.places.slice(0, -1) };
		return top;
	}
}

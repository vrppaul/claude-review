/**
 * The time now, for whatever on screen says how long ago something was.
 *
 * One clock for the whole review, and it ticks only while something drawn
 * reads it: a dozen questions waiting on the agent run one timer, and a
 * review with nothing waiting runs none.
 */

import { createSubscriber } from 'svelte/reactivity';

// How often what is said in seconds moves on
const TICK_EVERY = 1000;

/** Tell whoever reads the clock that it moved, every tick, until nobody reads it. */
function tickEverySecond(moved: () => void): () => void {
	const ticking = setInterval(moved, TICK_EVERY);
	return () => clearInterval(ticking);
}

export class Clock {
	readonly #readFrom = createSubscriber(tickEverySecond);

	/** The time now. Read while drawing, it moves on once a second. */
	get now(): number {
		this.#readFrom();
		return Date.now();
	}
}

/**
 * Something done once a frame the browser draws, for as long as it is kept
 * up: how the page follows what the browser tells of no move of. A stretch
 * of text is pushed down by whatever is drawn above it — a thread that
 * arrives, an image read in — with nothing scrolled or resized, so where it
 * stands is read again each frame. For a reading that costs as little as
 * that one; what looks through the page waits to be told it changed.
 */
export class EveryFrame {
	readonly #run: () => void;
	#awaited: number;

	/** @param run what is done each frame, from the next one on */
	constructor(run: () => void) {
		this.#run = run;
		this.#awaited = requestAnimationFrame(this.#turn);
	}

	/** Done with: nothing is run again. */
	stop(): void {
		cancelAnimationFrame(this.#awaited);
	}

	readonly #turn = (): void => {
		this.#awaited = requestAnimationFrame(this.#turn);
		this.#run();
	};
}

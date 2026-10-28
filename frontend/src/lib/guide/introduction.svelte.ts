/**
 * A way of working the guide introduces to a reader once — Story at the
 * switch, Send feedback under Help — as far as this page knows.
 *
 * Whether it was introduced is kept by the server, for every review on the
 * machine. Until the server says, the page does not know, and introduces
 * nothing: better not introduced than introduced twice. It counts as
 * introduced once the guide notes it — where the reader said not to show it
 * again, or tried it, and for Story where its news or the tour showed it —
 * and is to be introduced again where they undo "Don't show again". Not
 * kept, that is said: the reader chose, and the next review would introduce
 * it again without a word why.
 */

/** Whether a way of working has been introduced to the reader, as far as this page knows: before the server says, it does not. */
type Introduced = 'unknown' | 'introduced' | 'not';

export class Introduction {
	// Keep whether it was introduced, for every review
	readonly #keep: (introduced: boolean) => Promise<unknown>;
	// Say that it could not be kept, as the page says what a request came to
	readonly #notKept: (error: unknown) => void;
	#introduced = $state<Introduced>('unknown');

	constructor(keep: (introduced: boolean) => Promise<unknown>, notKept: (error: unknown) => void) {
		this.#keep = keep;
		this.#notKept = notKept;
	}

	/** Whether it is still to be introduced: the server said it never was, and nothing on this page has since. */
	get due(): boolean {
		return this.#introduced === 'not';
	}

	/** Learn what the server keeps: a reader who tried the way while it was asked has been introduced to it, whatever it kept. */
	learn(kept: boolean): void {
		if (this.#introduced === 'unknown') this.#introduced = kept ? 'introduced' : 'not';
	}

	/**
	 * It has been introduced, or tried: kept, for every review, and never introduced again. Kept also before the
	 * server has said whether it was before, which then changes nothing.
	 */
	note(): void {
		if (this.#introduced === 'introduced') return;
		this.#introduced = 'introduced';
		this.#keep(true).catch(this.#notKept);
	}

	/** The reader undid "Don't show again": it is introduced again, here and in every review. */
	again(): void {
		this.#introduced = 'not';
		this.#keep(false).catch(this.#notKept);
	}
}

/**
 * Where the page stands with the review it shows: open on it, or over.
 *
 * The page learns the review is over in one of three ways: this tab sends
 * it for good, the review says so as it ends, or the socket finds another
 * review answering on the port. Once over it stays over, and the first way
 * it ended is the one kept: it decides whether the draft is done with.
 */

/** How the review ended, as this page learned it. */
export type Ending =
	/** Sent for good, here or in another tab, or ended once everything had gone: its draft is done with. */
	| 'finished'
	/** Stopped under the reader — Ctrl+C, its server stopping, a fault: what was not sent is kept. */
	| 'stopped'
	/** Another review answers on this port now: this one is gone, and what was not sent is kept. */
	| 'replaced';

export class ServerLink {
	#ending = $state<Ending | null>(null);
	readonly #ended: PromiseWithResolvers<Ending> = Promise.withResolvers();

	/** How the review ended, or null while it runs. */
	get ending(): Ending | null {
		return this.#ending;
	}

	/** Settles once the review is over, with how it ended, for whoever lets go of it then. */
	get ended(): Promise<Ending> {
		return this.#ended.promise;
	}

	/** The review is over; whatever said so first is how it ended. */
	end(ending: Ending): void {
		if (this.#ending !== null) return;
		this.#ending = ending;
		this.#ended.resolve(ending);
	}
}

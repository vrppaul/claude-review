/**
 * Where the page stands with the review it shows: reached, being reached
 * again, or over.
 *
 * The socket says which: a socket dropped is a review the page is trying to
 * reach again, and one its own review welcomes is a review reached. While it
 * is not reached nothing is sent — the send would only fail — and what the
 * reader writes waits in the draft as before.
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

/** Where the page stands with its review. */
export type LinkState = 'connected' | 'reconnecting' | 'ended';

export class ServerLink {
	// Whether the review answers on the page's socket now: it did as the page opened
	#reachable = $state(true);
	#ending = $state<Ending | null>(null);
	readonly #ended: PromiseWithResolvers<Ending> = Promise.withResolvers();

	/** Where the page stands with its review now. */
	get state(): LinkState {
		if (this.#ending !== null) return 'ended';
		return this.#reachable ? 'connected' : 'reconnecting';
	}

	/** Whether the review can be sent anything now: reached, and not over. */
	get connected(): boolean {
		return this.state === 'connected';
	}

	/** How the review ended, or null while it runs. */
	get ending(): Ending | null {
		return this.#ending;
	}

	/** Settles once the review is over, with how it ended, for whoever lets go of it then. */
	get ended(): Promise<Ending> {
		return this.#ended.promise;
	}

	/** The socket dropped: the page is trying to reach the review again. */
	lost(): void {
		this.#reachable = false;
	}

	/** The page's own review welcomed it on a socket again. */
	reached(): void {
		this.#reachable = true;
	}

	/** The review is over; whatever said so first is how it ended. */
	end(ending: Ending): void {
		if (this.#ending !== null) return;
		this.#ending = ending;
		this.#ended.resolve(ending);
	}
}

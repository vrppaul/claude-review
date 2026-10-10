/**
 * Sending the review: the summary written for it, the rounds sent while it
 * stays open, and the end.
 */

import { endReview, submitReview } from '$lib/api/review-api';
import type { Rounds } from '$lib/review/rounds.svelte';
import type { Threads } from '$lib/review/threads.svelte';
import type { SubmitResponse } from '$lib/types';
import { threadOnTheWire } from '$lib/api/thread-wire';

export class Submission {
	readonly #threads: Threads;
	readonly #rounds: Rounds;
	// The summary: about the change as a whole, not one line of it
	#body: string;
	#finished = $state(false);
	// Settled once the review is over, for whoever lets go of it then
	readonly #over = Promise.withResolvers<void>();

	/** @param body the summary of an unsent review of the same thing, picked up where it stopped */
	constructor(threads: Threads, rounds: Rounds, body: string) {
		this.#threads = threads;
		this.#rounds = rounds;
		this.#body = $state(body);
	}

	get body(): string {
		return this.#body;
	}

	/** Whether the review is over — sent for good, or ended — and the page is done. */
	get finished(): boolean {
		return this.#finished;
	}

	/** Settles once the review is over: sent for good, or ended. */
	get over(): Promise<void> {
		return this.#over.promise;
	}

	/** Whether there is anything to send at all. */
	get hasContent(): boolean {
		return this.#threads.count > 0 || this.#body.trim().length > 0;
	}

	/** Whether there is anything the answering side has not been told yet. */
	get hasUnsent(): boolean {
		return this.#threads.unsent.length > 0 || this.#body.trim().length > 0;
	}

	setBody(text: string): void {
		this.#body = text;
	}

	/**
	 * Send what has been written since the last time.
	 *
	 * `end` decides whether this is the last word: a round leaves the review
	 * open, so the answers to it have somewhere to come back to.
	 */
	async submit(end: boolean): Promise<SubmitResponse> {
		const summary = this.#body.trim();
		const unsent = this.#threads.unsent;

		const result = await submitReview({
			threads: unsent.map(threadOnTheWire),
			...(summary ? { body: summary } : {}),
			end
		});

		if (end) {
			this.#finish();
			return result;
		}

		// A round is a line under what was said, not the end of it: the threads
		// stay, and only what happens next is new
		this.#threads.markSent(unsent, result.round);
		this.setBody('');
		this.#rounds.reach(result.round + 1);
		return result;
	}

	/** End a review that was being worked through in rounds. */
	async end(): Promise<void> {
		await endReview();
		this.#finish();
	}

	#finish(): void {
		this.#finished = true;
		this.#over.resolve();
	}
}

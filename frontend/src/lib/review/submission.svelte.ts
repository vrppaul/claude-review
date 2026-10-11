/**
 * Sending the review: the summary written for it, the pane it is sent
 * from, the rounds sent while it stays open, and the end.
 *
 * Whether the review goes out as a round or for good is decided here, once:
 * a round is only worth sending while an agent is there to work through it,
 * and on its own, sending is the end of the review. The button and the keys
 * that send it ask the same question of the same place.
 */

import { endReview, submitReview } from '$lib/api/review-api';
import type { Answerer } from '$lib/review/answerer.svelte';
import type { Rounds } from '$lib/review/rounds.svelte';
import type { ServerLink } from '$lib/review/server-link.svelte';
import type { Threads } from '$lib/review/threads.svelte';
import type { SubmitResponse } from '$lib/types';
import { threadOnTheWire } from '$lib/api/thread-wire';
import { messageOf } from '$lib/utils/errors';

export class Submission {
	readonly #threads: Threads;
	readonly #rounds: Rounds;
	readonly #answerer: Answerer;
	readonly #link: ServerLink;
	// The summary: about the change as a whole, not one line of it
	#body: string;
	// Whether the pane the review is sent from is open
	#finishing = $state(false);
	// Something is on its way to the server: nothing more is sent until it is answered
	#sending = $state(false);
	// Why the last send did not go, until the next one is tried
	#failed = $state<string | null>(null);
	// Settled once this page has sent the review for good, or ended it
	readonly #over: PromiseWithResolvers<void> = Promise.withResolvers();

	/**
	 * @param answerer whoever answers the review, whose presence decides between a round and the end
	 * @param link the page's tie to the review, which this ends once the review is sent for good
	 * @param body the summary of an unsent review of the same thing, picked up where it stopped
	 */
	constructor(threads: Threads, rounds: Rounds, answerer: Answerer, link: ServerLink, body: string) {
		this.#threads = threads;
		this.#rounds = rounds;
		this.#answerer = answerer;
		this.#link = link;
		this.#body = $state(body);
	}

	get body(): string {
		return this.#body;
	}

	/** Settles once this page has sent the review for good, or ended it. */
	get over(): Promise<void> {
		return this.#over.promise;
	}

	/** Whether an agent is there to work through rounds, so what is sent is a round rather than the end. */
	get inRounds(): boolean {
		return this.#answerer.attached;
	}

	/** Whether there is anything to send at all. */
	get hasContent(): boolean {
		return this.#threads.count > 0 || this.#body.trim().length > 0;
	}

	/** Whether there is anything the answering side has not been told yet. */
	get hasUnsent(): boolean {
		return this.#threads.unsent.length > 0 || this.#body.trim().length > 0;
	}

	/** Whether sending now would send something: a round needs news, the end needs anything at all. */
	get canSend(): boolean {
		return !this.#sending && this.#link.ending === null && (this.inRounds ? this.hasUnsent : this.hasContent);
	}

	/** Whether a send is on its way. */
	get sending(): boolean {
		return this.#sending;
	}

	/** Why the last send did not go, if it did not. */
	get failed(): string | null {
		return this.#failed;
	}

	/** Whether the pane the review is sent from is open. */
	get finishing(): boolean {
		return this.#finishing;
	}

	setFinishing(open: boolean): void {
		this.#finishing = open;
	}

	setBody(text: string): void {
		this.#body = text;
	}

	/**
	 * Send what the pane offers: a round while an agent works through them,
	 * the review for good otherwise. A failure is said, not thrown: the pane
	 * stays open with everything in it.
	 */
	async send(): Promise<void> {
		if (!this.canSend) return;
		await this.#attempt(() => this.submit(!this.inRounds));
	}

	/** End a review that was being worked through in rounds, saying why if it could not be. */
	async end(): Promise<void> {
		if (await this.#attempt(() => endReview())) this.#finish();
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

	/** Do one send, once at a time, and put the pane away if it went; whether it went. */
	async #attempt(act: () => Promise<unknown>): Promise<boolean> {
		if (this.#sending) return false;
		this.#sending = true;
		this.#failed = null;
		try {
			await act();
			this.#finishing = false;
			return true;
		} catch (error) {
			this.#failed = messageOf(error);
			return false;
		} finally {
			this.#sending = false;
		}
	}

	#finish(): void {
		this.#link.end('finished');
		this.#over.resolve();
	}
}

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

	/** Whether there is anything to send at all: a thread, the summary, or a comment still open in its field. */
	get hasContent(): boolean {
		return this.#threads.count > 0 || this.#body.trim().length > 0 || this.#threads.open.length > 0;
	}

	/** Whether there is anything the answering side has not been told yet, comments still open included. */
	get hasUnsent(): boolean {
		return this.#threads.unsent.length > 0 || this.#body.trim().length > 0 || this.#threads.open.length > 0;
	}

	/**
	 * Whether sending now would send something: a round needs news, the end
	 * needs anything at all, and either needs the review to be reached.
	 */
	get canSend(): boolean {
		return !this.#sending && this.#link.connected && (this.inRounds ? this.hasUnsent : this.hasContent);
	}

	/** Whether the review can be ended now: nothing on its way, and the review reached. */
	get canEnd(): boolean {
		return !this.#sending && this.#link.connected;
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

	/**
	 * End a review that was being worked through in rounds, saying why if it
	 * could not be. Whatever has not gone yet goes with the end, as the
	 * final review — the way a review nobody worked through ends — and only
	 * a review with nothing left to send is simply ended.
	 */
	async end(): Promise<void> {
		if (!this.canEnd) return;
		if (this.hasUnsent) {
			await this.#attempt(() => this.submit(true));
			return;
		}
		if (await this.#attempt(() => endReview())) this.#finish();
	}

	/**
	 * Send what has been written since the last time, comments still open in
	 * their fields included.
	 *
	 * `end` decides whether this is the last word: a round leaves the review
	 * open, so the answers to it have somewhere to come back to.
	 */
	async submit(end: boolean): Promise<SubmitResponse> {
		this.#threads.sayOpen();
		const written = this.#body;
		const summary = written.trim();
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
		// stay, and only what happens next is new — what was written while the
		// round was on its way included
		this.#threads.markSent(unsent, result.round);
		this.#takeSent(written);
		this.#rounds.reach(result.round + 1);
		return result;
	}

	/**
	 * Let go of the summary that went with a round. What was added to it while
	 * the round was on its way belongs to the next one, and a summary
	 * rewritten meanwhile is all new.
	 */
	#takeSent(written: string): void {
		if (this.#body.startsWith(written)) this.#body = this.#body.slice(written.length).trimStart();
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

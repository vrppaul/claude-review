/**
 * Which threads have gone out, and in which round. A round carries what is
 * new since the last one, not the whole review again — and the reader can
 * see which of what is on screen the answering side has already read.
 *
 * Only the reader makes a thread new again: writing in it, editing,
 * settling or deleting it. An answer from the agent, or the thread
 * following its lines onto a diff taken again, tells the agent nothing it
 * did not write or cannot see. A round still on its way when the reader
 * changes a thread did not carry it as it now is, so it goes with the next.
 */

import { SvelteMap } from 'svelte/reactivity';

import type { Thread } from '$lib/types';

/** A thread a round carries, and how many times the reader had changed it when the round went. */
export interface CarriedThread {
	id: string;
	readerChanges: number;
}

export class ThreadSending {
	// The round each thread went out in, by thread
	readonly #sentIn = new SvelteMap<string, number>();
	// How many times the reader has changed each thread, by thread
	readonly #readerChanges = new SvelteMap<string, number>();

	/** @param sent the round each thread had gone out in before a reload, by thread */
	constructor(sent: Record<string, number>) {
		for (const [threadId, round] of Object.entries(sent)) this.#sentIn.set(threadId, round);
	}

	/** The round a thread went out in, or nothing if it has not yet. */
	roundOf(threadId: string): number | undefined {
		return this.#sentIn.get(threadId);
	}

	/** The round every thread sent so far went out in, by thread, as the draft keeps them. */
	get rounds(): Record<string, number> {
		return Object.fromEntries(this.#sentIn);
	}

	/** A thread that arrives as the agent wrote it: it has nothing in it the agent has not read. */
	arrivedSent(threadId: string, round: number): void {
		this.#sentIn.set(threadId, round);
	}

	/** The reader changed a thread: it goes with the next round, whatever a round on its way carried. */
	changedByReader(threadId: string): void {
		this.#sentIn.delete(threadId);
		this.#readerChanges.set(threadId, this.#readerChangesTo(threadId) + 1);
	}

	/** The threads a round about to go carries, as `markSent` is handed them back once it has gone. */
	carry(threads: readonly Thread[]): CarriedThread[] {
		return threads.map((thread) => ({ id: thread.id, readerChanges: this.#readerChangesTo(thread.id) }));
	}

	/** Note that the threads a round carried went out in it, but for those the reader changed since. */
	markSent(carried: readonly CarriedThread[], round: number): void {
		for (const { id, readerChanges } of carried) {
			if (this.#readerChangesTo(id) === readerChanges) this.#sentIn.set(id, round);
		}
	}

	#readerChangesTo(threadId: string): number {
		return this.#readerChanges.get(threadId) ?? 0;
	}
}

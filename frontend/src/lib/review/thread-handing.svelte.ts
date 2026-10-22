/**
 * What the agent has of each thread, as the review says whenever it hands
 * one over — with a round, a question, a message pointing at it, or to an
 * agent reading it — said by id: its opening by the thread's own id, as a
 * question names it, and each turn by its own.
 *
 * The agent reads a thread once, as it is handed it, so what it has is the
 * reader's to rewrite and delete no more: they say more after it instead.
 * The review refuses a thread that comes back changed in it; this page
 * offers no way to. Kept with the draft, so a reload offers no more than
 * before it.
 */

import { SvelteMap } from 'svelte/reactivity';

/** What the agent has of a thread nothing of which was handed over: nothing. */
const NOTHING_HANDED: readonly string[] = [];

export class ThreadHanding {
	// What the agent has of each thread, by thread: everything said in it, by id
	readonly #handed = new SvelteMap<string, readonly string[]>();

	/** @param handed what the agent had of each thread before a reload, or as the review says, by thread */
	constructor(handed: Record<string, string[]>) {
		this.handedOver(handed);
	}

	/** The review handed threads over: this is everything the agent now has of each, by thread. */
	handedOver(handed: Record<string, readonly string[]>): void {
		for (const [threadId, said] of Object.entries(handed)) this.#handed.set(threadId, said);
	}

	/** Whether the agent has something said in a thread: its opening by the thread's own id, a turn by its own. */
	has(threadId: string, saidId: string): boolean {
		return (this.#handed.get(threadId) ?? NOTHING_HANDED).includes(saidId);
	}

	/** What the agent has of each thread, by thread, as the draft keeps it. */
	get kept(): Record<string, string[]> {
		return Object.fromEntries([...this.#handed].map(([threadId, said]) => [threadId, [...said]]));
	}
}

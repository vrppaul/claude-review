/**
 * What the agent has of each thread, as the review says it — on every
 * opening of the page, whenever it hands one over (with a round, a question,
 * a message pointing at it, to an agent reading it), when the agent raises
 * one, and when the page catches up — said here by id: its opening by the
 * thread's own id, as a question names it, and each turn by its own.
 *
 * The agent reads a thread as it is handed it, so what it has is the
 * reader's to rewrite and delete no more: they say more after it instead.
 * The review alone keeps it, and says it again whenever the page opens: a
 * draft keeps none of it.
 */

import { SvelteMap } from 'svelte/reactivity';

import type { ThreadAsHanded } from '$lib/types';

/** What the agent has of a thread nothing of which was handed over: nothing. */
const NOTHING_HANDED: readonly string[] = [];

export class ThreadHanding {
	// What the agent has of each thread, by thread: everything said in it, by id
	readonly #handed = new SvelteMap<string, readonly string[]>();

	/** The review says what the agent now has of these threads, by thread. */
	handedOver(handed: Record<string, ThreadAsHanded>): void {
		for (const [threadId, has] of Object.entries(handed)) {
			this.#handed.set(threadId, [threadId, ...has.turns.map((turn) => turn.turn_id)]);
		}
	}

	/** Whether the agent has something said in a thread: its opening by the thread's own id, a turn by its own. */
	has(threadId: string, saidId: string): boolean {
		return (this.#handed.get(threadId) ?? NOTHING_HANDED).includes(saidId);
	}
}

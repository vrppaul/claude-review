/**
 * What the agent has of each thread, as the review says it — on every
 * opening of the page, whenever it hands one over (with a round, a question,
 * a message pointing at it, to an agent reading it), when the agent raises
 * one, and when the page catches up — said here by id: its opening by the
 * thread's own id, as a question names it, and each turn by its own.
 *
 * The agent reads a thread as it is handed it, so what it has is the
 * reader's to rewrite and delete no more: they say more after it instead.
 * What the reader said that it does not have, or a thread settled or opened
 * again since it was last handed, goes with the next round; the round it
 * first had the thread in is what the thread says it went out in. The
 * review alone keeps all of it, and says it again whenever the page opens: a
 * draft keeps none of it. A review restarted mid-way knows of nothing handed,
 * its agent perhaps another, so what went out before goes again: sent twice
 * costs the agent a second look, never sent costs the reader the comment.
 */

import { SvelteMap } from 'svelte/reactivity';

import type { Thread, ThreadAsHanded } from '$lib/types';
import { READER } from '$lib/utils/speakers';

export class ThreadHanding {
	// What the agent has of each thread, by thread, as the review last said it
	readonly #handed = new SvelteMap<string, ThreadAsHanded>();

	/** The review says what the agent now has of these threads, by thread. */
	handedOver(handed: Record<string, ThreadAsHanded>): void {
		for (const [threadId, has] of Object.entries(handed)) this.#handed.set(threadId, has);
	}

	/** Whether the agent has something said in a thread: its opening by the thread's own id, a turn by its own. */
	has(threadId: string, saidId: string): boolean {
		const handed = this.#handed.get(threadId);
		return handed !== undefined && (saidId === threadId || handed.turns.some((turn) => turn.turn_id === saidId));
	}

	/** The round the agent first had a thread in, which the thread says it went out in; nothing while it has none of it. */
	roundOf(threadId: string): number | undefined {
		return this.#handed.get(threadId)?.round;
	}

	/**
	 * Whether a thread holds what the agent does not have, and so goes with
	 * the next round: something the reader said in it, or its settling. The
	 * agent's own words it has already, however they reached the page.
	 */
	lacks(thread: Thread): boolean {
		return (
			this.#lacksOpening(thread) ||
			thread.turns.some((turn) => turn.author === READER && !this.has(thread.id, turn.id)) ||
			thread.resolved !== this.#toldSettled(thread.id)
		);
	}

	/** Whether the reader opened a thread the agent has not been handed. */
	#lacksOpening(thread: Thread): boolean {
		return thread.raised_by === READER && !this.has(thread.id, thread.id);
	}

	/** Whether a thread was settled when the agent was last handed it: one never handed was told of no settling. */
	#toldSettled(threadId: string): boolean {
		return this.#handed.get(threadId)?.resolved ?? false;
	}
}

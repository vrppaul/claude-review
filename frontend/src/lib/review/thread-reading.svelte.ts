/**
 * How this page reads the threads, apart from what the threads say: which
 * are folded away, which carry an answer nobody has looked at, and which
 * questions are with the agent and not answered yet.
 *
 * None of it goes on the wire — it is how the threads are read, not what
 * they say — so folding a thread or reading its answer tells the server
 * nothing. It is kept with the draft all the same: a reload should not
 * unfold what was folded, nor forget what is still being waited on.
 */

import { SvelteMap, SvelteSet } from 'svelte/reactivity';

import type { ThreadsRead } from '$lib/drafts/draft-shapes';
import type { AwaitedQuestion } from '$lib/types';

/** What a thread with nothing asked of it is waiting for: nothing. */
const NOTHING_AWAITED: readonly AwaitedQuestion[] = [];

export class ThreadReading {
	readonly #folded = new SvelteSet<string>();
	readonly #unread = new SvelteSet<string>();
	// Questions with the agent, by thread, oldest first
	readonly #awaiting = new SvelteMap<string, AwaitedQuestion[]>();

	isFolded(threadId: string): boolean {
		return this.#folded.has(threadId);
	}

	/** Fold a thread away, to get its space back without settling it, or bring it back. */
	setFolded(threadId: string, folded: boolean): void {
		if (folded) this.#folded.add(threadId);
		else this.#folded.delete(threadId);
	}

	/** Whether an answer arrived in the thread that nobody has looked at. */
	isUnread(threadId: string): boolean {
		return this.#unread.has(threadId);
	}

	markUnread(threadId: string): void {
		this.#unread.add(threadId);
	}

	markRead(threadId: string): void {
		this.#unread.delete(threadId);
	}

	markAllRead(): void {
		this.#unread.clear();
	}

	/** The questions in a thread still with the agent, oldest first. */
	awaiting(threadId: string): readonly AwaitedQuestion[] {
		return this.#awaiting.get(threadId) ?? NOTHING_AWAITED;
	}

	/** A question in the thread was handed over, and is now waited on. */
	asked(threadId: string, questionId: string): void {
		const waiting = this.awaiting(threadId);
		this.#awaiting.set(threadId, [...waiting, { id: questionId, at: Date.now() }]);
	}

	/** A question is no longer waited on: answered, or never handed over. */
	settled(threadId: string, questionId: string | undefined): void {
		const waiting = this.awaiting(threadId).filter((question) => question.id !== questionId);
		if (waiting.length === 0) this.#awaiting.delete(threadId);
		else this.#awaiting.set(threadId, waiting);
	}

	/** The thread is gone: nothing about reading it is worth keeping. */
	forget(threadId: string): void {
		this.#folded.delete(threadId);
		this.#unread.delete(threadId);
		this.#awaiting.delete(threadId);
	}

	/** How the threads were being read, as the draft keeps it. */
	get kept(): ThreadsRead {
		return {
			folded: [...this.#folded],
			unread: [...this.#unread],
			awaiting: Object.fromEntries(this.#awaiting)
		};
	}

	/** Pick up how the threads were being read before a reload. */
	pickUp(read: ThreadsRead): void {
		for (const threadId of read.folded) this.#folded.add(threadId);
		for (const threadId of read.unread) this.#unread.add(threadId);
		for (const [threadId, waiting] of Object.entries(read.awaiting)) {
			this.#awaiting.set(threadId, waiting);
		}
	}
}

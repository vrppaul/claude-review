/**
 * How this page reads the threads, apart from what the threads say: which
 * are folded away, which turns of a long one are folded behind its row of
 * earlier replies, which carry an answer nobody has looked at, which
 * questions are with the agent and not answered yet, and which the reader
 * took back.
 *
 * None of it goes on the wire — it is how the threads are read, not what
 * they say — so folding a thread or reading its answer tells the server
 * nothing. It is kept with the draft all the same: a reload should not
 * unfold what was folded, nor forget what is still being waited on. All
 * but the earlier turns folded, which a reload works out anew.
 */

import { SvelteMap, SvelteSet } from 'svelte/reactivity';

import type { ThreadsRead } from '$lib/drafts/draft-shapes';
import type { AwaitedQuestion, TakenBackQuestion } from '$lib/types';

/** What a thread with nothing asked of it is waiting for: nothing. */
const NOTHING_AWAITED: readonly AwaitedQuestion[] = [];
/** The answers known to be unread in a thread new for some other reason: none. */
const NO_ANSWERS: readonly string[] = [];

/** The turns of a thread folded behind its row of earlier replies, by id, and whether the reader opened the row. */
export interface TurnsFolded {
	turns: readonly string[];
	open: boolean;
}

export class ThreadReading {
	readonly #folded = new SvelteSet<string>();
	/**
	 * The earlier turns folded in each thread, worked out as its turns are
	 * first drawn and kept while it stays open, so nothing folds under the
	 * reader's eyes: none for a thread not drawn open since the page loaded
	 * or since it was last folded whole.
	 */
	readonly #turnsFolded = new SvelteMap<string, TurnsFolded>();
	/**
	 * Threads with something nobody has looked at, and which of their
	 * answers that is, by id: none for a thread the agent raised, whose
	 * opening is what is new, nor for one a reload brought back unread — the
	 * draft keeps that a thread is unread, not which answers made it so.
	 */
	readonly #unread = new SvelteMap<string, readonly string[]>();
	// Questions with the agent, by thread, oldest first
	readonly #awaiting = new SvelteMap<string, AwaitedQuestion[]>();
	// Questions the reader took back while they were waited on, by thread, and when
	readonly #takenBack = new SvelteMap<string, TakenBackQuestion[]>();

	/** @param read how the threads were being read before a reload */
	constructor(read: ThreadsRead) {
		for (const threadId of read.folded) this.#folded.add(threadId);
		for (const threadId of read.unread) this.#unread.set(threadId, NO_ANSWERS);
		for (const [threadId, waiting] of Object.entries(read.awaiting)) {
			this.#awaiting.set(threadId, waiting);
		}
		for (const [threadId, takenBack] of Object.entries(read.takenBack)) {
			this.#takenBack.set(threadId, takenBack);
		}
	}

	isFolded(threadId: string): boolean {
		return this.#folded.has(threadId);
	}

	/**
	 * Fold a thread away, to get its space back without settling it, or bring
	 * it back. Folded, it lets go of its earlier turns folded, which its next
	 * opening works out anew.
	 */
	setFolded(threadId: string, folded: boolean): void {
		if (folded) {
			this.#folded.add(threadId);
			this.#turnsFolded.delete(threadId);
		} else {
			this.#folded.delete(threadId);
		}
	}

	/** The earlier turns folded in a thread; none until its turns are first drawn. */
	turnsFolded(threadId: string): TurnsFolded | undefined {
		return this.#turnsFolded.get(threadId);
	}

	/** Fold these turns of a thread behind its row of earlier replies, the row shut. */
	foldTurns(threadId: string, turns: readonly string[]): void {
		this.#turnsFolded.set(threadId, { turns, open: false });
	}

	/** Open a thread's row of earlier replies: the turns it folds stand under it. */
	showFoldedTurns(threadId: string): void {
		const folded = this.#turnsFolded.get(threadId);
		if (folded) this.#turnsFolded.set(threadId, { ...folded, open: true });
	}

	/** Whether an answer arrived in the thread that nobody has looked at. */
	isUnread(threadId: string): boolean {
		return this.#unread.has(threadId);
	}

	/** Something in the thread is new — the thread itself, raised by the agent. */
	markUnread(threadId: string): void {
		if (!this.#unread.has(threadId)) this.#unread.set(threadId, NO_ANSWERS);
	}

	/** An answer arrived in the thread, and nobody has looked at it yet. */
	answerArrived(threadId: string, answerId: string): void {
		this.#unread.set(threadId, [...(this.#unread.get(threadId) ?? NO_ANSWERS), answerId]);
	}

	/** Whether an answer arrived after the reader last looked at its thread. */
	isNewAnswer(threadId: string, answerId: string): boolean {
		return this.#unread.get(threadId)?.includes(answerId) ?? false;
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

	/** A question in the thread was handed over, and is now waited on: one taken back before is asked again. */
	asked(threadId: string, questionId: string): void {
		const waiting = this.awaiting(threadId);
		this.#awaiting.set(threadId, [...waiting, { id: questionId, at: Date.now() }]);
		const takenBack = this.#takenBack.get(threadId)?.filter((question) => question.id !== questionId);
		if (takenBack !== undefined) this.#takenBack.set(threadId, takenBack);
	}

	/**
	 * Take an answer that came back: the question it answers is no longer
	 * waited on. An answer that names its question is believed; one that does
	 * not answers the oldest still waited on, the order they were handed over
	 * in. Says which question it answered, if it answered one.
	 */
	settleAnswer(threadId: string, named: string | null): string | undefined {
		const answered = named ?? this.awaiting(threadId).at(0)?.id;
		this.settled(threadId, answered);
		return answered;
	}

	/** A question is no longer waited on: answered, or never handed over. */
	settled(threadId: string, questionId: string | undefined): void {
		const waiting = this.awaiting(threadId).filter((question) => question.id !== questionId);
		if (waiting.length === 0) this.#awaiting.delete(threadId);
		else this.#awaiting.set(threadId, waiting);
	}

	/** A question waited on was taken back by the reader: it is waited on no more, and stays seen as taken back. */
	tookBack(threadId: string, questionId: string): void {
		this.settled(threadId, questionId);
		const takenBack = this.#takenBack.get(threadId) ?? [];
		this.#takenBack.set(threadId, [...takenBack, { id: questionId, at: Date.now() }]);
	}

	/** When the reader took back a question of the thread, if they did. */
	takenBackAt(threadId: string, questionId: string): number | undefined {
		return this.#takenBack.get(threadId)?.find((question) => question.id === questionId)?.at;
	}

	/** The thread is gone: nothing about reading it is worth keeping. */
	forget(threadId: string): void {
		this.#folded.delete(threadId);
		this.#turnsFolded.delete(threadId);
		this.#unread.delete(threadId);
		this.#awaiting.delete(threadId);
		this.#takenBack.delete(threadId);
	}

	/** How the threads were being read, as the draft keeps it. */
	get kept(): ThreadsRead {
		return {
			folded: [...this.#folded],
			unread: [...this.#unread.keys()],
			awaiting: Object.fromEntries(this.#awaiting),
			takenBack: Object.fromEntries(this.#takenBack)
		};
	}
}

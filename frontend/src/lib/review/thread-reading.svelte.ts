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
import type { AwaitedQuestion, TakenBackQuestion, Thread } from '$lib/types';
import { READER } from '$lib/utils/speakers';
import { drawnTurnsOf, exchangesOf, turnsToFold, type TurnsFolded } from '$lib/utils/thread-exchanges';

/** What a thread with nothing asked of it is waiting for: nothing. */
const NOTHING_AWAITED: readonly AwaitedQuestion[] = [];
/** The answers known to be unread in a thread new for some other reason: none. */
const NO_ANSWERS: readonly string[] = [];
/** The earlier turns folded in a thread whose turns are not drawn: none. */
const NOTHING_FOLDED: TurnsFolded = { turns: [], opened: [] };

/** What keeps a thread's turns in sight that only its card knows. */
export interface InSightOnTheCard {
	/** Whether the reader's words in this turn are being rewritten. */
	rewriting: (turnId: string) => boolean;
	/** Whether handing the thread over failed, which is said under its last question. */
	askFailed: boolean;
}

export class ThreadReading {
	readonly #folded = new SvelteSet<string>();
	// The earlier turns folded in each thread drawn open, kept while it stays open: nothing folds under the reader
	readonly #turnsFolded = new SvelteMap<string, TurnsFolded>();
	/**
	 * Threads with something nobody has looked at, and which of their
	 * answers that is, by id: none for a thread the agent raised, whose
	 * opening is what is new.
	 */
	readonly #unread = new SvelteMap<string, readonly string[]>();
	// Questions with the agent, by thread, oldest first
	readonly #awaiting = new SvelteMap<string, AwaitedQuestion[]>();
	// Questions the reader took back while they were waited on, by thread, and when
	readonly #takenBack = new SvelteMap<string, TakenBackQuestion[]>();

	/** @param read how the threads were being read before a reload */
	constructor(read: ThreadsRead) {
		for (const threadId of read.folded) this.#folded.add(threadId);
		for (const [threadId, answers] of Object.entries(read.unread)) this.#unread.set(threadId, answers);
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

	/** Fold a thread away, to get its space back without settling it, or bring it back. */
	setFolded(threadId: string, folded: boolean): void {
		if (folded) {
			this.#folded.add(threadId);
			// Its next opening works its earlier turns folded out anew
			this.#turnsFolded.delete(threadId);
		} else {
			this.#folded.delete(threadId);
		}
	}

	/** The earlier turns folded in a thread; none until its turns are drawn. */
	turnsFolded(threadId: string): TurnsFolded {
		return this.#turnsFolded.get(threadId) ?? NOTHING_FOLDED;
	}

	/** A thread's turns are drawn: their earlier ones fold where no fold is held, so a card drawn again keeps its own. */
	foldAsDrawn(thread: Thread, card: InSightOnTheCard): void {
		if (!this.#turnsFolded.has(thread.id)) this.foldEarlierTurns(thread, card);
	}

	/** Fold what lies between the comment that opened a thread and its last turns, every row shut, but what stays in sight. */
	foldEarlierTurns(thread: Thread, card: InSightOnTheCard): void {
		const drawn = drawnTurnsOf(exchangesOf(thread)).map((turn) => turn.id);
		// The question asked last: the reader's last reply, or the comment that opened the thread
		const lastQuestion = thread.turns.findLast((turn) => turn.author === READER)?.id ?? thread.id;
		const turns = turnsToFold(drawn, (turnId) => this.#staysInSight(thread.id, turnId, card, lastQuestion));
		this.#turnsFolded.set(thread.id, { turns, opened: [] });
	}

	/** Open one row of a thread's earlier replies: the folded turns it holds stand under it. */
	showFoldedTurns(threadId: string, turns: readonly string[]): void {
		const folded = this.#turnsFolded.get(threadId);
		if (folded) this.#turnsFolded.set(threadId, { ...folded, opened: [...folded.opened, ...turns] });
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

	/**
	 * Whether a turn must stay in sight: an answer not read yet, a question
	 * still with the agent, words being rewritten, and the question asking
	 * failed on, the failure under it.
	 */
	#staysInSight(threadId: string, turnId: string, card: InSightOnTheCard, lastQuestion: string): boolean {
		return (
			this.isNewAnswer(threadId, turnId) ||
			this.awaiting(threadId).some((question) => question.id === turnId) ||
			card.rewriting(turnId) ||
			(card.askFailed && turnId === lastQuestion)
		);
	}

	/** How the threads were being read, as the draft keeps it. */
	get kept(): ThreadsRead {
		return {
			folded: [...this.#folded],
			unread: Object.fromEntries(this.#unread),
			awaiting: Object.fromEntries(this.#awaiting),
			takenBack: Object.fromEntries(this.#takenBack)
		};
	}
}
